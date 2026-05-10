"""Tests for the prompt-caching changes shipped 2026-05-10.

Verifies that the OpenAI + Anthropic adapters split the user prompt into
a static prefix (cached) and a volatile INPUT block (uncached), and that
the legacy plain-string content shape is preserved when caching is
disabled via the `ai_prompt_cache_enabled=False` setting.
"""
from __future__ import annotations

from app.ai.providers.anthropic_adapter import AnthropicProvider
from app.ai.providers.openai_adapter import (
    OpenAIProvider,
    _split_user_prompt,
)
from app.ai.types import AITaskName, ProviderRequest
from app.config import Settings


def _settings(*, cache_enabled: bool = True) -> Settings:
    return Settings.model_validate(
        {
            "openai_api_key": "test-key",
            "openai_model": "claude-test",
            "openai_base_url": "https://openrouter.ai/api/v1",
            "anthropic_api_key": "test-key",
            "anthropic_model": "claude-test",
            "ai_prompt_cache_enabled": cache_enabled,
        }
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        task=AITaskName.ALERT_EXPLANATION,
        model="claude-test",
        system_prompt="You are an AML analyst assistant.",
        user_prompt=(
            "TASK:\nALERT_EXPLANATION\n\n"
            "GUIDANCE:\nExplain the alert.\n\n"
            "OUTPUT_SCHEMA:\n{}\n\n"
            "INPUT:\n{\"alert_id\":\"abc\"}"
        ),
        output_schema_name="AlertExplanation",
        output_schema={"type": "object"},
    )


# Splitter ------------------------------------------------------------------


def test_split_user_prompt_separates_static_prefix_from_input() -> None:
    prompt = (
        "TASK:\nfoo\n\nGUIDANCE:\nbar\n\nOUTPUT_SCHEMA:\n{}\n\nINPUT:\n{\"x\":1}"
    )
    static, dynamic = _split_user_prompt(prompt)
    assert static.endswith("INPUT:\n")
    assert dynamic == '{"x":1}'


def test_split_user_prompt_returns_full_prompt_when_no_input_marker() -> None:
    prompt = "TASK:\nfoo (no INPUT marker present)"
    static, dynamic = _split_user_prompt(prompt)
    assert static == prompt
    assert dynamic == ""


# OpenAI adapter ------------------------------------------------------------


def test_openai_messages_use_cache_control_when_enabled() -> None:
    provider = OpenAIProvider(_settings(cache_enabled=True))
    messages = provider._build_messages(_request())

    assert len(messages) == 2

    system = messages[0]
    assert system["role"] == "system"
    assert isinstance(system["content"], list)
    assert system["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert "AML analyst" in system["content"][0]["text"]

    user = messages[1]
    assert user["role"] == "user"
    assert isinstance(user["content"], list)
    # Two blocks: cached static prefix + uncached volatile INPUT.
    assert len(user["content"]) == 2
    assert user["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert user["content"][0]["text"].endswith("INPUT:\n")
    # Volatile block has no cache_control marker.
    assert "cache_control" not in user["content"][1]
    assert user["content"][1]["text"] == '{"alert_id":"abc"}'


def test_openai_messages_fall_back_to_legacy_shape_when_disabled() -> None:
    provider = OpenAIProvider(_settings(cache_enabled=False))
    messages = provider._build_messages(_request())

    assert len(messages) == 2
    assert messages[0] == {
        "role": "system",
        "content": "You are an AML analyst assistant.",
    }
    # Legacy single-string user content.
    assert messages[1]["role"] == "user"
    assert isinstance(messages[1]["content"], str)
    assert messages[1]["content"].endswith('INPUT:\n{"alert_id":"abc"}')


# Anthropic adapter — static unit assertions ---------------------------------


def test_anthropic_provider_initialises_with_cache_setting() -> None:
    """Anthropic adapter applies the cache_control split inline in
    generate_json. We don't replicate the message assembly as a public
    helper there because Anthropic's payload shape differs (system is a
    top-level field, not a message). This test just guards the config
    plumbing — the adapter reads ai_prompt_cache_enabled from settings.
    """
    enabled = AnthropicProvider(_settings(cache_enabled=True))
    disabled = AnthropicProvider(_settings(cache_enabled=False))

    assert enabled.settings.ai_prompt_cache_enabled is True
    assert disabled.settings.ai_prompt_cache_enabled is False
