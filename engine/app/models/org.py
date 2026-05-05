import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    org_type: Mapped[str] = mapped_column(String(32))
    bank_code: Mapped[str | None] = mapped_column(String(32))
    plan: Mapped[str] = mapped_column(String(32), default="standard")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan_id: Mapped[str] = mapped_column(String(32), default="starter")
    plan_overrides: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_set_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_status: Mapped[str | None] = mapped_column(String(32))
    stripe_price_id: Mapped[str | None] = mapped_column(String(64))
    plan_grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
