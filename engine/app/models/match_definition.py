import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchDefinition(Base):
    __tablename__ = "match_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_hits: Mapped[int] = mapped_column(Integer, default=0)


class MatchExecution(Base):
    __tablename__ = "match_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("match_definitions.id", ondelete="CASCADE"))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_status: Mapped[str] = mapped_column(String(32), default="completed")
    results_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
