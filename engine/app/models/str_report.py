import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class STRReport(TimestampMixin, Base):
    __tablename__ = "str_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    report_ref: Mapped[str] = mapped_column(String(64))
    report_type: Mapped[str] = mapped_column(String(16), default="str")
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    subject_name: Mapped[str | None] = mapped_column(String(255))
    subject_account: Mapped[str] = mapped_column(String(128))
    subject_bank: Mapped[str | None] = mapped_column(String(255))
    subject_phone: Mapped[str | None] = mapped_column(String(64))
    subject_wallet: Mapped[str | None] = mapped_column(String(64))
    subject_nid: Mapped[str | None] = mapped_column(String(64))
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(16), default="BDT")
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    primary_channel: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(64))
    narrative: Mapped[str | None] = mapped_column(String)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    date_range_start: Mapped[date | None] = mapped_column(Date())
    date_range_end: Mapped[date | None] = mapped_column(Date())
    auto_risk_score: Mapped[int | None] = mapped_column(Integer)
    matched_entity_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    cross_bank_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
