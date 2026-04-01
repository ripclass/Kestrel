import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class STRReport(TimestampMixin, Base):
    __tablename__ = "str_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    report_ref: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    subject_name: Mapped[str | None] = mapped_column(String(255))
    subject_account: Mapped[str] = mapped_column(String(128))
    subject_phone: Mapped[str | None] = mapped_column(String(64))
    subject_wallet: Mapped[str | None] = mapped_column(String(64))
    subject_nid: Mapped[str | None] = mapped_column(String(64))
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(64))
    narrative: Mapped[str | None] = mapped_column(String)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    date_range_start: Mapped[datetime | None] = mapped_column(Date())
    date_range_end: Mapped[datetime | None] = mapped_column(Date())
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
