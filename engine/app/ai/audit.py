import json
import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import AuthenticatedUser
from app.database import engine
from app.observability import current_request_id

AuditSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
logger = logging.getLogger("kestrel.ai.audit")


def _uuid_or_none(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _redact_text(payload: object) -> str:
    """Render the redacted payload as JSON text for the outcome-log corpus.

    The orchestrator already calls ``redact_payload`` before invoking a
    provider, so the value reaching us here is the redacted form. We
    serialise to JSON for stability — keeps the prompt in a deterministic
    shape that re-parses cleanly during V3 phase 4 fine-tune training.
    """
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(payload)


async def record_ai_invocation(
    *,
    user: AuthenticatedUser,
    task: str,
    provider: str,
    model: str,
    prompt_version: str,
    redaction_mode: str,
    input_payload: object,
    output_payload: object,
    schema_name: str,
    fallback_used: bool,
    attempt_count: int,
    ip: str | None = None,
    latency_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    confidence: float | None = None,
    fallback_from_provider: str | None = None,
    fallback_from_model: str | None = None,
) -> uuid.UUID | None:
    """Dual-write: one row to ``audit_log`` for compliance, one row to
    ``ai_outcome_log`` for the V3 sovereign-AI training corpus.

    Returns the inserted ``ai_outcome_log.id`` so the orchestrator can
    surface it back to UI callers — when an analyst later edits the
    AI-drafted output, the correction-capture endpoint flips
    ``analyst_correction`` on this same row.

    Pre-V3 callers used the ``bool`` return type; the new ``uuid | None``
    is backward-compatible at the truthy-check level (any non-None UUID
    is truthy, ``None`` is falsy) so existing call sites still work.
    """
    details = {
        "task": task,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "redaction_mode": redaction_mode,
        "schema_name": schema_name,
        "fallback_used": fallback_used,
        "attempt_count": attempt_count,
        "input_digest": _digest(input_payload),
        "output_digest": _digest(output_payload),
    }

    request_id = current_request_id() or None
    outcome_log_id = uuid.uuid4()
    prompt_redacted = _redact_text(input_payload)
    prompt_digest = _digest(input_payload)
    safe_output = output_payload if isinstance(output_payload, dict) else {"value": output_payload}

    async with AuditSessionLocal() as session:
        try:
            # 1. Compliance audit row (existing behaviour — pre-V3 callers depend on this).
            await session.execute(
                text(
                    """
                    insert into audit_log (
                        org_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        details,
                        ip
                    ) values (
                        :org_id,
                        :user_id,
                        :action,
                        :resource_type,
                        :resource_id,
                        cast(:details as jsonb),
                        :ip
                    )
                    """
                ),
                {
                    "org_id": _uuid_or_none(user.org_id),
                    "user_id": _uuid_or_none(user.user_id),
                    "action": "ai.invoke",
                    "resource_type": "ai_task",
                    "resource_id": outcome_log_id,
                    "details": json.dumps(details, ensure_ascii=True),
                    "ip": ip,
                },
            )

            # 2. Outcome-log row (V3 phase 1.1 — training corpus).
            await session.execute(
                text(
                    """
                    insert into ai_outcome_log (
                        id,
                        org_id,
                        task_name,
                        provider,
                        model,
                        prompt_redacted,
                        prompt_digest,
                        output_json,
                        confidence,
                        latency_ms,
                        prompt_tokens,
                        completion_tokens,
                        fallback_from_provider,
                        fallback_from_model,
                        request_id
                    ) values (
                        :id,
                        :org_id,
                        :task_name,
                        :provider,
                        :model,
                        :prompt_redacted,
                        :prompt_digest,
                        cast(:output_json as jsonb),
                        :confidence,
                        :latency_ms,
                        :prompt_tokens,
                        :completion_tokens,
                        :fallback_from_provider,
                        :fallback_from_model,
                        :request_id
                    )
                    """
                ),
                {
                    "id": outcome_log_id,
                    "org_id": _uuid_or_none(user.org_id),
                    "task_name": task,
                    "provider": provider,
                    "model": model,
                    "prompt_redacted": prompt_redacted,
                    "prompt_digest": prompt_digest,
                    "output_json": json.dumps(safe_output, ensure_ascii=True),
                    "confidence": confidence,
                    "latency_ms": int(latency_ms) if latency_ms is not None else 0,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "fallback_from_provider": fallback_from_provider,
                    "fallback_from_model": fallback_from_model,
                    "request_id": request_id,
                },
            )
            await session.commit()
            return outcome_log_id
        except Exception as exc:  # noqa: BLE001 — never let outcome logging break the AI path.
            await session.rollback()
            logger.warning(
                "ai.audit.write_failed",
                extra={"error_type": type(exc).__name__, "task": task, "provider": provider},
            )
            return None


async def record_outcome_correction(
    *,
    log_id: uuid.UUID,
    user: AuthenticatedUser,
    correction: dict[str, Any] | None,
    outcome_label: str | None,
) -> bool:
    """Update an existing ``ai_outcome_log`` row with the analyst's
    correction or outcome label. Used by the V3 phase 1.3 endpoints.

    Returns True if the row was updated. Enforces own-org-only at the SQL
    layer so a caller cannot mutate another tenant's rows even though the
    engine connects as ``postgres`` (BYPASSRLS).
    """
    if outcome_label is not None and outcome_label not in {
        "true_positive",
        "false_positive",
        "accepted",
        "rejected",
        "edited",
    }:
        return False

    async with AuditSessionLocal() as session:
        try:
            result = await session.execute(
                text(
                    """
                    update ai_outcome_log
                       set analyst_correction = coalesce(cast(:correction as jsonb), analyst_correction),
                           outcome_label = coalesce(:outcome_label, outcome_label),
                           updated_at = now()
                     where id = :log_id
                       and org_id = :org_id
                    """
                ),
                {
                    "log_id": log_id,
                    "org_id": _uuid_or_none(user.org_id),
                    "correction": json.dumps(correction, ensure_ascii=True) if correction is not None else None,
                    "outcome_label": outcome_label,
                },
            )
            await session.commit()
            return (result.rowcount or 0) > 0
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.warning(
                "ai.outcome.correction_failed",
                extra={"error_type": type(exc).__name__, "log_id": str(log_id)},
            )
            return False
