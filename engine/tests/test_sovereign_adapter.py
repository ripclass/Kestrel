"""Pure-helper coverage for the V3 phase 4.4 sovereign adapter.

The async ``generate_json`` path needs a live HTTP endpoint; this file
pins the deterministic helpers — content extraction from a vLLM/OpenAI-
shaped response, token-usage extraction, and the log-prob → confidence
conversion.
"""
from __future__ import annotations

import math

from app.ai.providers.sovereign_adapter import (
    SovereignProvider,
    _extract_content,
    _extract_token_usage,
    confidence_from_logprobs,
    parse_chat_completion_content,
)
from app.ai.types import ProviderName
from app.config import Settings


# Content extraction -------------------------------------------------------

def test_extract_content_string_message() -> None:
    payload = {
        "choices": [
            {"message": {"content": '{"narrative": "ok"}'}},
        ],
    }
    assert _extract_content(payload) == '{"narrative": "ok"}'


def test_extract_content_segment_list() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "first "},
                        {"type": "text", "text": "second"},
                    ]
                }
            }
        ],
    }
    assert _extract_content(payload) == "first second"


def test_extract_content_empty_choices() -> None:
    assert _extract_content({"choices": []}) == ""
    assert _extract_content({}) == ""


def test_parse_chat_completion_content_alias_matches_internal() -> None:
    """The public alias is what tests + V3 P5 quality gates import; it
    must stay byte-equivalent to the internal helper."""
    payload = {"choices": [{"message": {"content": "hello"}}]}
    assert parse_chat_completion_content(payload) == _extract_content(payload)


# Token usage --------------------------------------------------------------

def test_extract_token_usage_returns_pair() -> None:
    payload = {"usage": {"prompt_tokens": 120, "completion_tokens": 64}}
    assert _extract_token_usage(payload) == (120, 64)


def test_extract_token_usage_handles_missing() -> None:
    assert _extract_token_usage({}) == (None, None)
    assert _extract_token_usage({"usage": {}}) == (None, None)


def test_extract_token_usage_coerces_floats() -> None:
    """Some providers ship token counts as floats; we coerce to int."""
    payload = {"usage": {"prompt_tokens": 120.0, "completion_tokens": 64.0}}
    assert _extract_token_usage(payload) == (120, 64)


# Log-prob → confidence ----------------------------------------------------

def test_confidence_from_logprobs_high_confidence_response() -> None:
    """Tokens with logprobs near 0 (probabilities near 1) lift the mean
    high — but the cap at 0.95 prevents claiming 100%."""
    payload = {
        "choices": [
            {
                "logprobs": {
                    "content": [
                        {"logprob": math.log(0.99)},
                        {"logprob": math.log(0.97)},
                        {"logprob": math.log(0.99)},
                    ],
                }
            }
        ],
    }
    score = confidence_from_logprobs(payload)
    assert score is not None
    assert 0.9 <= score <= 0.95


def test_confidence_from_logprobs_low_confidence_response() -> None:
    payload = {
        "choices": [
            {
                "logprobs": {
                    "content": [
                        {"logprob": math.log(0.4)},
                        {"logprob": math.log(0.3)},
                        {"logprob": math.log(0.5)},
                    ],
                }
            }
        ],
    }
    score = confidence_from_logprobs(payload)
    assert score is not None
    assert score < 0.5


def test_confidence_from_logprobs_capped_at_ninety_five() -> None:
    """Even synthetically perfect logprobs cap at 0.95."""
    payload = {
        "choices": [
            {
                "logprobs": {
                    "content": [
                        {"logprob": 0.0},  # exp(0) = 1.0
                        {"logprob": 0.0},
                    ],
                }
            }
        ],
    }
    score = confidence_from_logprobs(payload)
    assert score == 0.95


def test_confidence_from_logprobs_handles_missing_data() -> None:
    """Missing logprobs return None — the orchestrator falls back to
    ``compute_schema_validity``."""
    assert confidence_from_logprobs({}) is None
    assert confidence_from_logprobs({"choices": []}) is None
    assert confidence_from_logprobs({"choices": [{}]}) is None
    assert confidence_from_logprobs({"choices": [{"logprobs": {"content": []}}]}) is None


def test_confidence_from_logprobs_skips_malformed_entries() -> None:
    """Defensive: a token without a logprob field doesn't crash."""
    payload = {
        "choices": [
            {
                "logprobs": {
                    "content": [
                        {"logprob": math.log(0.9)},
                        {"token": "x"},  # no logprob
                        "not-a-dict",
                        {"logprob": math.log(0.8)},
                    ],
                }
            }
        ],
    }
    score = confidence_from_logprobs(payload)
    assert score is not None
    assert 0.7 < score < 0.9


# Provider configuration ---------------------------------------------------

def _settings(**overrides) -> Settings:
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_sovereign_provider_missing_config() -> None:
    p = SovereignProvider(_settings())
    detail = p._missing_config_detail()
    assert detail is not None
    assert "AI_SOVEREIGN_URL" in detail
    assert "AI_SOVEREIGN_MODEL" in detail


def test_sovereign_provider_partial_config() -> None:
    p = SovereignProvider(_settings(ai_sovereign_url="http://x"))
    detail = p._missing_config_detail()
    assert detail is not None
    assert "AI_SOVEREIGN_MODEL" in detail


def test_sovereign_provider_fully_configured() -> None:
    p = SovereignProvider(_settings(ai_sovereign_url="http://x", ai_sovereign_model="kestrel-v1"))
    assert p._missing_config_detail() is None


def test_sovereign_provider_name_is_enum() -> None:
    p = SovereignProvider(_settings())
    assert p.name == ProviderName.SOVEREIGN


def test_sovereign_provider_omits_auth_header_when_no_key() -> None:
    p = SovereignProvider(_settings(ai_sovereign_url="http://x", ai_sovereign_model="m"))
    headers = p._headers()
    assert "Authorization" not in headers
    assert headers["Content-Type"] == "application/json"


def test_sovereign_provider_includes_auth_header_when_key_set() -> None:
    p = SovereignProvider(_settings(ai_sovereign_url="http://x", ai_sovereign_model="m", ai_sovereign_api_key="secret"))
    headers = p._headers()
    assert headers["Authorization"] == "Bearer secret"


# Request body -------------------------------------------------------------

def test_build_request_body_carries_logprobs_flag() -> None:
    """The adapter relies on logprobs being requested — without them
    the confidence source is empty and the routing falls back to
    schema-validity."""
    from app.ai.types import AITaskName, ProviderRequest

    p = SovereignProvider(_settings(ai_sovereign_url="http://x", ai_sovereign_model="m"))
    request = ProviderRequest(
        task=AITaskName.ALERT_EXPLANATION,
        model="m",
        system_prompt="sys",
        user_prompt="user",
        output_schema_name="S",
        output_schema={},
    )
    body = p._build_request_body(request)
    assert body["logprobs"] is True
    assert body["top_logprobs"] == 5
    assert body["model"] == "m"
    assert len(body["messages"]) == 2
