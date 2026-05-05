import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RealtimeScoringLog(Base):
    __tablename__ = "realtime_scoring_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    transaction_external_id: Mapped[str] = mapped_column(Text)
    request_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    score: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list] = mapped_column(JSONB, default=list)
    cross_bank_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str | None] = mapped_column(Text)
    feedback_received: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback_outcome: Mapped[str | None] = mapped_column(String(32))
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
