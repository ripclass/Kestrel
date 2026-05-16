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
    # Migration 026: MLPA 2012 §2(cc) predicate-offence pre-population on the
    # typology row. Tells the alert / STR / dissemination workflow which
    # predicate to pre-fill when this typology fires.
    predicate_offences: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    # Optional MLPA / ATA enabling clause cited on the source row.
    mlpa_section: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True)
    # BFIU citation key — for BD-TBML rows this is the §2.4.x.x section
    # number in the TBML Guidelines 2019 so a reviewer can trace back.
    bfiu_avenue_ref: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
