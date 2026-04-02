import asyncio

from app.ai.redaction import redact_payload
from app.ai.routing import resolve_task_routes
from app.ai.service import AIOrchestrator
from app.ai.types import AITaskName, ProviderName
from app.auth import DEMO_USERS
from app.config import Settings
from app.schemas.ai import AlertExplanationResult, CaseSummaryResult


def build_settings(**overrides) -> Settings:
    base = {
        "app_name": "Kestrel Engine",
        "app_version": "0.1.0",
        "environment": "test",
        "engine_port": 8000,
        "allowed_origins": "http://localhost:3000",
        "database_url": "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        "redis_url": "redis://localhost:6379/0",
        "storage_bucket_uploads": "kestrel-uploads",
        "storage_bucket_exports": "kestrel-exports",
        "kestrel_enable_demo_mode": True,
        "kestrel_demo_persona": "bfiu_analyst",
        "ai_enable_external_probes": False,
        "ai_provider_timeout_seconds": 5.0,
        "ai_redaction_mode": "redact",
        "ai_fallback_enabled": True,
        "openai_base_url": "https://api.openai.com/v1",
        "anthropic_base_url": "https://api.anthropic.com",
        "anthropic_version": "2023-06-01",
    }
    base.update(overrides)
    return Settings.model_validate(base)


class FakeInvalidProvider:
    name = ProviderName.OPENAI

    async def healthcheck(self, probe: bool = False):  # pragma: no cover - unused in test
        raise NotImplementedError

    async def generate_json(self, request):
        return type("Response", (), {"content": '{"unexpected": true}'})()


class FakeHeuristicProvider:
    name = ProviderName.HEURISTIC

    async def healthcheck(self, probe: bool = False):  # pragma: no cover - unused in test
        raise NotImplementedError

    async def generate_json(self, request):
        return type(
            "Response",
            (),
            {
                "content": (
                    '{"summary":"Analyst-readable summary","why_it_matters":"Cross-bank exposure remains active.",'
                    '"recommended_actions":["Escalate to case","Request beneficiary KYC"]}'
                )
            },
        )()


def test_redaction_masks_sensitive_fields() -> None:
    payload = {
        "account": "1781430000701",
        "phone": "01712345678",
        "email": "analyst@bfiu.gov.bd",
        "nid": "1987654321098",
    }

    redacted = redact_payload(payload, "redact")

    assert redacted["account"] == "[REDACTED_ACCOUNT]"
    assert redacted["phone"] == "[REDACTED_PHONE]"
    assert redacted["email"] == "[REDACTED_EMAIL]"
    assert redacted["nid"] == "[REDACTED_NID]"


def test_routes_append_heuristic_fallback_in_demo_mode() -> None:
    settings = build_settings(
        openai_api_key="openai-test",
        openai_model="gpt-test",
        anthropic_api_key="anthropic-test",
        anthropic_model="claude-test",
    )

    routes = resolve_task_routes(AITaskName.ALERT_EXPLANATION, settings)

    assert [route.provider for route in routes] == [
        ProviderName.ANTHROPIC,
        ProviderName.OPENAI,
        ProviderName.HEURISTIC,
    ]


def test_orchestrator_falls_back_after_schema_failure() -> None:
    settings = build_settings(
        openai_api_key="openai-test",
        openai_model="gpt-test",
    )
    calls: list[dict[str, object]] = []

    async def fake_audit_logger(**kwargs):
        calls.append(kwargs)
        return True

    orchestrator = AIOrchestrator(
        settings=settings,
        providers={
            ProviderName.OPENAI: FakeInvalidProvider(),
            ProviderName.HEURISTIC: FakeHeuristicProvider(),
        },
        audit_logger=fake_audit_logger,
    )

    result = asyncio.run(
        orchestrator.invoke(
            task=AITaskName.ALERT_EXPLANATION,
            payload={
                "description": "Rapid cashout with repeated outbound movement.",
                "reasons": [{"rule": "rapid_cashout"}],
            },
            output_model=AlertExplanationResult,
            user=DEMO_USERS["bfiu_analyst"],
        )
    )

    assert result.provider == ProviderName.HEURISTIC
    assert result.fallback_used is True
    assert len(result.attempts) == 2
    assert calls and calls[0]["fallback_used"] is True


def test_orchestrator_returns_typed_case_summary_with_heuristic_provider() -> None:
    settings = build_settings()
    orchestrator = AIOrchestrator(settings=settings)

    result = asyncio.run(
        orchestrator.invoke(
            task=AITaskName.CASE_SUMMARY,
            payload={
                "title": "Rizwana Enterprise network investigation",
                "summary": "Multi-bank merchant front with rapid cashout and wallet fan-out.",
                "linked_entity_ids": ["ent-rizwana-account", "ent-rizwana-phone"],
                "notes": ["Counterparty KYC packet requested from Sonali Bank."],
            },
            output_model=CaseSummaryResult,
            user=DEMO_USERS["bfiu_analyst"],
        )
    )

    assert result.task == AITaskName.CASE_SUMMARY
    assert result.output.executive_summary
    assert isinstance(result.output.recommended_actions, list)
