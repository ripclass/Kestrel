from copy import deepcopy

from app.schemas.alert import AlertDetail, AlertReason, AlertSummary
from app.schemas.case import CaseSummary, CaseWorkspace
from app.schemas.intelligence import CrossBankMatch, TypologySummary
from app.schemas.investigate import ActivityEvent, EntityDossier, EntitySearchResult, ReportingHistoryItem
from app.schemas.network import GraphEdge, GraphNode, NetworkGraph
from app.schemas.report import ComplianceScore
from app.schemas.scan import DetectionRunSummary, FlaggedAccount

ENTITIES = [
    EntitySearchResult(
        id="ent-rizwana-account",
        entity_type="account",
        display_value="1781430000701",
        display_name="Rizwana Enterprise",
        canonical_value="1781430000701",
        risk_score=94,
        severity="critical",
        confidence=0.97,
        status="investigating",
        report_count=7,
        reporting_orgs=["Sonali Bank", "BRAC Bank", "Dutch-Bangla Bank"],
        total_exposure=22_140_000,
        tags=["rapid_cashout", "cross_bank", "commercial_front"],
    ),
    EntitySearchResult(
        id="ent-rizwana-phone",
        entity_type="phone",
        display_value="01712XXXXXX",
        display_name="Rizwana Enterprise Contact",
        canonical_value="01712xxxxxx",
        risk_score=82,
        severity="high",
        confidence=0.82,
        status="active",
        report_count=4,
        reporting_orgs=["BRAC Bank", "Islami Bank"],
        total_exposure=9_200_000,
        tags=["linked_phone", "merchant_intake"],
    ),
]

GRAPH = NetworkGraph(
    focus_entity_id="ent-rizwana-account",
    stats={"node_count": 5, "edge_count": 6, "max_depth": 3, "suspicious_paths": 2},
    nodes=[
        GraphNode(id="ent-rizwana-account", type="account", label="1781430000701", subtitle="Rizwana Enterprise", risk_score=94, severity="critical"),
        GraphNode(id="ent-rizwana-phone", type="phone", label="01712XXXXXX", subtitle="Shared contact", risk_score=82, severity="high"),
        GraphNode(id="ent-beneficiary-a", type="account", label="207810004901", subtitle="Beneficiary account", risk_score=73, severity="high"),
        GraphNode(id="ent-beneficiary-b", type="account", label="540022100018", subtitle="Second layer", risk_score=65, severity="medium"),
        GraphNode(id="ent-wallet", type="wallet", label="01XXXXXXXX", subtitle="Cashout wallet", risk_score=88, severity="high"),
    ],
    edges=[
        GraphEdge(id="edge-1", source="ent-rizwana-account", target="ent-beneficiary-a", label="BDT 14.0M", relation="transacted", amount=14_000_000),
        GraphEdge(id="edge-2", source="ent-beneficiary-a", target="ent-wallet", label="BDT 8.1M", relation="transacted", amount=8_100_000),
        GraphEdge(id="edge-3", source="ent-rizwana-account", target="ent-rizwana-phone", label="shared contact", relation="shared_phone"),
        GraphEdge(id="edge-4", source="ent-beneficiary-a", target="ent-beneficiary-b", label="BDT 4.2M", relation="transacted", amount=4_200_000),
        GraphEdge(id="edge-5", source="ent-rizwana-phone", target="ent-wallet", label="beneficiary alias", relation="beneficiary"),
        GraphEdge(id="edge-6", source="ent-rizwana-account", target="ent-wallet", label="cross-bank hit", relation="co_reported"),
    ],
)

ENTITY_DOSSIER = EntityDossier(
    **ENTITIES[0].model_dump(),
    narrative="Seven STRs across three banks converge on the same commercial account and linked phone identifiers.",
    linked_case_ids=["case-001"],
    linked_alert_ids=["alert-rapid-cashout", "alert-cross-bank"],
    reporting_history=[
        ReportingHistoryItem(org_name="Sonali Bank", report_ref="STR-2604-000112", reported_at="2026-04-01T16:10:00Z", channel="RTGS", amount=14_000_000),
        ReportingHistoryItem(org_name="BRAC Bank", report_ref="STR-2603-009221", reported_at="2026-03-29T09:20:00Z", channel="MFS", amount=3_800_000),
    ],
    connections=ENTITIES,
    timeline=[
        ActivityEvent(id="evt-1", title="Rapid cashout detected", description="83% of inbound RTGS moved within 12 minutes.", occurred_at="2026-04-01T16:22:00Z", actor="Kestrel Engine"),
        ActivityEvent(id="evt-2", title="Cross-bank match expanded", description="Phone and wallet identifiers linked to peer-bank reports.", occurred_at="2026-03-29T09:30:00Z", actor="Entity Resolver"),
    ],
    graph=GRAPH,
)

ALERTS = [
    AlertDetail(
        id="alert-rapid-cashout",
        title="Rizwana Enterprise rapid cashout",
        description="Large inbound RTGS cleared into multiple beneficiaries within minutes.",
        alert_type="rapid_cashout",
        risk_score=94,
        severity="critical",
        status="reviewing",
        created_at="2026-04-01T16:25:00Z",
        org_name="Bangladesh Financial Intelligence Unit",
        entity_id="ent-rizwana-account",
        reasons=[
            AlertReason(
                rule="rapid_cashout",
                score=75,
                weight=8,
                explanation="BDT 14,000,000 credited at 16:10 and 83% debited by 16:22 across RTGS and MFS exits.",
                evidence={"credit_amount": 14_000_000, "debit_percentage": 83, "time_gap_min": 12},
                recommended_action="Escalate to case and request beneficiary KYC pack.",
            ),
            AlertReason(
                rule="proximity_to_bad",
                score=55,
                weight=5,
                explanation="Recipient wallet already appears in three prior cross-bank reports.",
                evidence={"prior_banks": 3, "wallet": "01XXXXXXXX"},
            ),
        ],
        graph=GRAPH,
    )
]

MATCHES = [
    CrossBankMatch(
        id="match-001",
        entity_id="ent-rizwana-account",
        match_key="1781430000701",
        match_type="account",
        involved_orgs=["Sonali Bank", "BRAC Bank", "Dutch-Bangla Bank"],
        involved_str_ids=["STR-2604-000112", "STR-2603-009221", "STR-2602-007104"],
        match_count=3,
        total_exposure=22_140_000,
        risk_score=92,
        severity="critical",
        status="investigating",
    )
]

TYPOLOGIES = [
    TypologySummary(
        id="typology-merchant",
        title="Merchant front with rapid MFS exit",
        category="fraud",
        channels=["RTGS", "MFS"],
        indicators=["Rapid outbound after settlement", "Shared phone across multiple wallets"],
        narrative="Commercial accounts receive high-value settlements and immediately disperse funds into consumer wallets.",
    )
]

DETECTION_RUNS = [
    DetectionRunSummary(id="run-001", file_name="march-retail-scan.csv", status="completed", alerts_generated=18, accounts_scanned=2140, tx_count=40218, created_at="2026-04-01T05:10:00Z"),
    DetectionRunSummary(id="run-002", file_name="wallet-burst-scan.xlsx", status="processing", alerts_generated=4, accounts_scanned=920, tx_count=11884, created_at="2026-04-02T02:30:00Z"),
]

FLAGGED_ACCOUNTS = [
    FlaggedAccount(label="Likely mule account", score=94),
    FlaggedAccount(label="Secondary beneficiary cluster", score=82),
]

CASES = [
    CaseWorkspace(
        id="case-001",
        case_ref="KST-2604-00001",
        title="Rizwana Enterprise network investigation",
        summary="Multi-bank merchant front with rapid cashout and wallet fan-out.",
        severity="critical",
        status="investigating",
        total_exposure=22_140_000,
        assigned_to="Sadia Rahman",
        linked_entity_ids=["ent-rizwana-account", "ent-rizwana-phone"],
        timeline=ENTITY_DOSSIER.timeline,
        evidence_entities=ENTITIES,
        notes=["Counterparty KYC packet requested from Sonali Bank.", "Wallet beneficiary mapping suggests third-party collection activity."],
    )
]

COMPLIANCE = [
    ComplianceScore(org_name="Sonali Bank", submission_timeliness=91, alert_conversion=74, peer_coverage=88, score=84),
    ComplianceScore(org_name="BRAC Bank", submission_timeliness=87, alert_conversion=79, peer_coverage=82, score=83),
    ComplianceScore(org_name="Dutch-Bangla Bank", submission_timeliness=63, alert_conversion=52, peer_coverage=70, score=62),
]


def clone_entity_dossier() -> EntityDossier:
    return EntityDossier.model_validate(deepcopy(ENTITY_DOSSIER.model_dump()))


def clone_alerts() -> list[AlertDetail]:
    return [AlertDetail.model_validate(deepcopy(item.model_dump())) for item in ALERTS]
