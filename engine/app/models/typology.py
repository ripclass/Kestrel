from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Typology(TimestampMixin, Base):
    __tablename__ = "typologies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    indicators: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    narrative: Mapped[str] = mapped_column(String)
