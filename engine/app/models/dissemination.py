import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Dissemination(Base):
    __tablename__ = "disseminations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    dissemination_ref: Mapped[str] = mapped_column(String(64))
    recipient_agency: Mapped[str] = mapped_column(String)
    recipient_type: Mapped[str] = mapped_column(String(32))
    # Typed Bangladesh-named authority for procurement-grade reporting (V3 BFIU
    # alignment). Nullable for back-compat — old rows still resolve via the
    # legacy recipient_type field. New flow always populates this.
    recipient_authority: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    # MLPA / ATA enabling clause cited on the dissemination (e.g. mlpa_24_3 for
    # spontaneous LEA dissemination, mlpa_24_4 for foreign-FIU exchange).
    mlpa_section: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True)
    # Marks a Circular-22 bank-to-bank exchange (distinct from BFIU outbound
    # dissemination). Drives separate audit + reporting cadence.
    circular_22_exchange: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # MLPA 2012 §2(cc) predicate offence categories — see migration 025.
    predicate_offences: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    subject_summary: Mapped[str] = mapped_column(String)
    linked_report_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    linked_entity_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    linked_case_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    disseminated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    disseminated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    classification: Mapped[str] = mapped_column(String(32), default="confidential")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
