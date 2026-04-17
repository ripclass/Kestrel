import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    case_ref: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="open")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    linked_alert_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    linked_entity_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    total_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    timeline: Mapped[dict] = mapped_column(JSONB, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    due_date: Mapped[datetime | None] = mapped_column(Date())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variant: Mapped[str] = mapped_column(String(32), default="standard")
    parent_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id")
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_from: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    proposal_decision: Mapped[str | None] = mapped_column(String(16))
    proposal_decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    proposal_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
