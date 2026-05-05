import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SovereignRollout(Base):
    __tablename__ = "sovereign_rollout"

    task_name: Mapped[str] = mapped_column(Text, primary_key=True)
    threshold: Mapped[float] = mapped_column(Numeric, default=1.01)
    rollout_pct: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SovereignPromotionLog(Base):
    __tablename__ = "sovereign_promotion_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adapter_path: Mapped[str] = mapped_column(Text)
    base_model: Mapped[str] = mapped_column(Text)
    candidate_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    gate_results: Mapped[list] = mapped_column(JSONB, default=list)
    all_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    ran_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ran_by: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
