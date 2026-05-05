import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentInvestigation(Base):
    __tablename__ = "agent_investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    hypothesis: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    suggested_actions: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    hops_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
