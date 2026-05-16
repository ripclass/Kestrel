from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.predicate_offence import PredicateOffence

RecipientType = Literal[
    "law_enforcement",
    "regulator",
    "foreign_fiu",
    "prosecutor",
    "other",
]

# Named Bangladesh recipient authorities under MLPA 2012 §23 + §24 + Circular 22.
# Each value is the stable code; UI maps to display labels separately.
RecipientAuthority = Literal[
    "bangladesh_police_cid",
    "anti_corruption_commission",
    "national_board_of_revenue",
    "dept_narcotics_control",
    "bangladesh_securities_exchange_commission",
    "insurance_dev_regulatory_authority",
    "microcredit_regulatory_authority",
    "dgfi",
    "nsi",
    "court_or_investigating_officer",
    "foreign_fiu_egmont",
    "bb_internal_dept",
    "peer_reporting_org_circular_22",
]

# Enabling clause cited on each dissemination. MLPA covers §23(1)(a–g) +
# §24(3) (spontaneous to LEA) + §24(4) (cross-border via agreement). ATA §15
# mirrors are included for terrorist-financing disseminations.
MlpaSection = Literal[
    "mlpa_23_1_a",
    "mlpa_23_1_b",
    "mlpa_23_1_c",
    "mlpa_23_1_d",
    "mlpa_23_1_e",
    "mlpa_23_1_f",
    "mlpa_23_1_g",
    "mlpa_24_3",
    "mlpa_24_4",
    "ata_15_1_a",
    "ata_15_1_b",
    "ata_15_1_c",
    "ata_15_1_d",
    "ata_15_1_e",
    "ata_15_1_f",
    "ata_15_1_g",
]

Classification = Literal[
    "public",
    "internal",
    "confidential",
    "restricted",
    "secret",
]


class DisseminationCreate(BaseModel):
    recipient_agency: str
    recipient_type: RecipientType
    # Typed Bangladesh authority — required for new dissemination flow; legacy
    # callers that haven't been migrated may omit and we fall back to the
    # recipient_type+agency pair for back-compat.
    recipient_authority: RecipientAuthority | None = None
    mlpa_section: MlpaSection | None = None
    circular_22_exchange: bool = False
    # MLPA 2012 §2(cc) predicate offence(s) cited on this dissemination. Empty
    # array is allowed for back-compat / legacy rows that haven't been tagged.
    predicate_offences: list[PredicateOffence] = Field(default_factory=list)
    subject_summary: str
    linked_report_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    classification: Classification = "confidential"
    metadata: dict[str, object] = Field(default_factory=dict)


class DisseminationSummary(BaseModel):
    id: str
    org_id: str
    org_name: str
    dissemination_ref: str
    recipient_agency: str
    recipient_type: RecipientType
    recipient_authority: RecipientAuthority | None = None
    mlpa_section: MlpaSection | None = None
    circular_22_exchange: bool = False
    predicate_offences: list[PredicateOffence] = Field(default_factory=list)
    subject_summary: str
    classification: Classification
    disseminated_by: str | None = None
    disseminated_at: datetime
    linked_report_count: int
    linked_entity_count: int
    linked_case_count: int
    created_at: datetime


class DisseminationDetail(DisseminationSummary):
    linked_report_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class DisseminationListResponse(BaseModel):
    disseminations: list[DisseminationSummary]


class DisseminationMutationResponse(BaseModel):
    dissemination: DisseminationDetail
