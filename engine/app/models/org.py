import uuid

from sqlalchemy import String
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
