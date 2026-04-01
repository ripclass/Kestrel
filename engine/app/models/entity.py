import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(32))
    canonical_value: Mapped[str] = mapped_column(String(255))
    display_value: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    risk_score: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str | None] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="active")
    source: Mapped[str] = mapped_column(String(32), default="system")
    reporting_orgs: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
