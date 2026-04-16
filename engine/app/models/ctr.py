import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CashTransactionReport(Base):
    __tablename__ = "cash_transaction_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    account_number: Mapped[str] = mapped_column(String(128))
    account_name: Mapped[str | None] = mapped_column(String(255))
    transaction_date: Mapped[date] = mapped_column(Date())
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(16), default="BDT")
    transaction_type: Mapped[str | None] = mapped_column(String(32))
    branch_code: Mapped[str | None] = mapped_column(String(32))
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
