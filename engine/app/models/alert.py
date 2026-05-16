import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("entities.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String)
    alert_type: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="open")
    reasons: Mapped[dict] = mapped_column(JSONB, default=list)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Migration 028 — TBML pipeline integration. Populated by TBML detection
    # rules (from rule YAML predicate_offences + bfiu_avenue_ref) so every
    # TBML alert auto-cites its regulatory mapping and links back to the
    # source trade row.
    predicate_offences: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    linked_trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, nullable=True)
    bfiu_avenue_ref: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True)
