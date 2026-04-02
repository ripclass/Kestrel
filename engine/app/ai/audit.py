import json
import hashlib
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import AuthenticatedUser
from app.database import engine

AuditSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _uuid_or_none(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


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
) -> bool:
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

    async with AuditSessionLocal() as session:
        try:
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
                    "resource_id": None,
                    "details": json.dumps(details, ensure_ascii=True),
                    "ip": ip,
                },
            )
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False
