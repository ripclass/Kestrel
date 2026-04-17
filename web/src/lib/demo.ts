import type {
  AlertSummary,
  ApiKeySummary,
  CaseSummary,
  ComplianceScore,
  DetectionRunSummary,
  EntityDossier,
  EntitySummary,
  MatchSummary,
  Persona,
  Viewer,
} from "@/types/domain";

const baseTime = new Date("2026-04-02T10:30:00Z").getTime();

export const demoViewers: Record<string, Viewer> = {
  bfiu_analyst: {
    id: "viewer-analyst",
    email: "analyst@bfiu.gov.bd",
    fullName: "Sadia Rahman",
    designation: "Deputy Director, Intelligence Analysis",
    role: "analyst",
    persona: "bfiu_analyst",
    orgId: "org-bfiu",
    orgName: "Bangladesh Financial Intelligence Unit",
    orgType: "regulator",
  },
  bank_camlco: {
    id: "viewer-bank",
    email: "camlco@sonali.example",
    fullName: "Mahmudul Karim",
    designation: "Chief AML Compliance Officer",
    role: "manager",
    persona: "bank_camlco",
    orgId: "org-sonali",
    orgName: "Sonali Bank PLC",
    orgType: "bank",
  },
  bfiu_director: {
    id: "viewer-director",
    email: "director@bfiu.gov.bd",
    fullName: "Farhana Sultana",
    designation: "Director, BFIU",
    role: "admin",
    persona: "bfiu_director",
    orgId: "org-bfiu",
    orgName: "Bangladesh Financial Intelligence Unit",
    orgType: "regulator",
  },
};

export const demoPersonaOptions: Array<{
  persona: Persona;
  shortLabel: string;
  title: string;
  description: string;
}> = [
  {
    persona: "bfiu_analyst",
    shortLabel: "Analyst",
    title: "BFIU Analyst",
    description: "Alert-first investigation view with entity search, casework, and graph tracing.",
  },
  {
    persona: "bfiu_director",
    shortLabel: "Director",
    title: "BFIU Director",
    description: "Command dashboard focused on national threat posture, trend shifts, and compliance oversight.",
  },
  {
    persona: "bank_camlco",
    shortLabel: "Bank",
    title: "Bank CAMLCO",
    description: "Bank-side posture view for transaction scans, threat alerts, and reporting readiness.",
  },
];

export const entities: EntitySummary[] = [
  {
    id: "ent-rizwana-account",
    entityType: "account",
    displayValue: "1781430000701",
    displayName: "Rizwana Enterprise",
    canonicalValue: "1781430000701",
    riskScore: 94,
    severity: "critical",
    confidence: 0.97,
    status: "investigating",
    reportCount: 7,
    reportingOrgs: ["Sonali Bank", "BRAC Bank", "Dutch-Bangla Bank"],
    totalExposure: 22140000,
    firstSeen: "2026-01-11T08:00:00Z",
    lastSeen: "2026-04-01T17:22:00Z",
    tags: ["rapid_cashout", "cross_bank", "commercial_front"],
  },
  {
    id: "ent-rizwana-phone",
    entityType: "phone",
    displayValue: "01712XXXXXX",
    displayName: "Rizwana Enterprise Contact",
    canonicalValue: "01712xxxxxx",
    riskScore: 82,
    severity: "high",
    confidence: 0.82,
    status: "active",
    reportCount: 4,
    reportingOrgs: ["BRAC Bank", "Islami Bank"],
    totalExposure: 9200000,
    firstSeen: "2026-02-08T05:00:00Z",
    lastSeen: "2026-03-29T12:18:00Z",
    tags: ["linked_phone", "merchant_intake"],
  },
  {
    id: "ent-bikash-wallet",
    entityType: "wallet",
    displayValue: "01XXXXXXXX",
    displayName: "MFS Collection Wallet",
    canonicalValue: "01xxxxxxxx",
    riskScore: 88,
    severity: "high",
    confidence: 0.9,
    status: "confirmed",
    reportCount: 5,
    reportingOrgs: ["bKash", "City Bank"],
    totalExposure: 11500000,
    firstSeen: "2025-12-14T10:00:00Z",
    lastSeen: "2026-04-02T05:30:00Z",
    tags: ["wallet_hub", "fan_out"],
  },
];

export const networkGraph: EntityDossier["graph"] = {
  focusEntityId: "ent-rizwana-account",
  stats: {
    nodeCount: 6,
    edgeCount: 7,
    maxDepth: 3,
    suspiciousPaths: 2,
  },
  nodes: [
    { id: "ent-rizwana-account", type: "account", label: "1781430000701", subtitle: "Rizwana Enterprise", riskScore: 94, severity: "critical" },
    { id: "ent-rizwana-phone", type: "phone", label: "01712XXXXXX", subtitle: "Shared contact", riskScore: 82, severity: "high" },
    { id: "ent-bikash-wallet", type: "wallet", label: "01XXXXXXXX", subtitle: "MFS cashout hub", riskScore: 88, severity: "high" },
    { id: "ent-beneficiary-a", type: "account", label: "207810004901", subtitle: "Beneficiary account", riskScore: 73, severity: "high" },
    { id: "ent-beneficiary-b", type: "account", label: "540022100018", subtitle: "Second-layer account", riskScore: 65, severity: "medium" },
    { id: "ent-owner", type: "person", label: "Nasrin Akter", subtitle: "Registered signatory", riskScore: 58, severity: "medium" },
  ],
  edges: [
    { id: "edge-1", source: "ent-rizwana-account", target: "ent-beneficiary-a", label: "BDT 14.0M", relation: "transacted", amount: 14000000 },
    { id: "edge-2", source: "ent-beneficiary-a", target: "ent-bikash-wallet", label: "BDT 8.1M", relation: "transacted", amount: 8100000 },
    { id: "edge-3", source: "ent-rizwana-account", target: "ent-rizwana-phone", label: "shared contact", relation: "shared_phone" },
    { id: "edge-4", source: "ent-owner", target: "ent-rizwana-account", label: "account holder", relation: "account_of" },
    { id: "edge-5", source: "ent-beneficiary-a", target: "ent-beneficiary-b", label: "BDT 4.2M", relation: "transacted", amount: 4200000 },
    { id: "edge-6", source: "ent-rizwana-phone", target: "ent-bikash-wallet", label: "beneficiary alias", relation: "beneficiary" },
    { id: "edge-7", source: "ent-rizwana-account", target: "ent-bikash-wallet", label: "cross-bank hit", relation: "co_reported" },
  ],
};

export const entityDossiers: Record<string, EntityDossier> = {
  "ent-rizwana-account": {
    ...entities[0],
    narrative:
      "Seven STRs across three banks converge on the same commercial account and linked phone identifiers. Funds are received in burst patterns, redistributed within minutes, and exit through wallet cashout routes.",
    linkedCaseIds: ["case-001"],
    linkedAlertIds: ["alert-rapid-cashout", "alert-cross-bank"],
    reportingHistory: [
      { orgName: "Sonali Bank", reportRef: "STR-2604-000112", reportedAt: "2026-04-01T16:10:00Z", channel: "RTGS", amount: 14000000 },
      { orgName: "BRAC Bank", reportRef: "STR-2603-009221", reportedAt: "2026-03-29T09:20:00Z", channel: "MFS", amount: 3800000 },
      { orgName: "Dutch-Bangla Bank", reportRef: "STR-2602-007104", reportedAt: "2026-02-14T05:40:00Z", channel: "NPSB", amount: 4340000 },
    ],
    connections: [entities[1], entities[2]],
    timeline: [
      { id: "evt-1", title: "Rapid cashout detected", description: "83% of inbound RTGS was transferred within 12 minutes.", occurredAt: "2026-04-01T16:22:00Z", actor: "Kestrel Engine" },
      { id: "evt-2", title: "Cross-bank match expanded", description: "Phone and wallet identifiers linked to two historical STRs from other banks.", occurredAt: "2026-03-29T09:30:00Z", actor: "Entity Resolver" },
      { id: "evt-3", title: "Analyst note added", description: "Commercial narrative does not support transaction tempo or beneficiary spread.", occurredAt: "2026-04-02T08:10:00Z", actor: "Sadia Rahman" },
    ],
    graph: networkGraph,
  },
};

export const alerts: AlertSummary[] = [
  {
    id: "alert-rapid-cashout",
    title: "Rizwana Enterprise rapid cashout",
    description: "Large inbound RTGS cleared into multiple beneficiaries within minutes.",
    alertType: "rapid_cashout",
    riskScore: 94,
    severity: "critical",
    status: "reviewing",
    createdAt: "2026-04-01T16:25:00Z",
    orgName: "Bangladesh Financial Intelligence Unit",
    entityId: "ent-rizwana-account",
    reasons: [
      {
        rule: "rapid_cashout",
        score: 75,
        weight: 8,
        explanation: "BDT 14,000,000 credited at 16:10 and 83% debited by 16:22 across RTGS and MFS exits.",
        evidence: { credit_amount: 14000000, debit_percentage: 83, time_gap_min: 12, channel: "RTGS" },
        recommendedAction: "Escalate to case and request beneficiary KYC pack.",
      },
      {
        rule: "proximity_to_bad",
        score: 55,
        weight: 5,
        explanation: "Recipient wallet already appears in three prior cross-bank reports.",
        evidence: { prior_banks: 3, nearest_flagged_wallet: "01XXXXXXXX" },
        recommendedAction: "Review linked wallet activity and shared devices.",
      },
    ],
  },
  {
    id: "alert-cross-bank",
    title: "Cross-bank identifier overlap",
    description: "Shared phone and wallet linked to prior STRs from three peer institutions.",
    alertType: "cross_bank",
    riskScore: 89,
    severity: "high",
    status: "open",
    createdAt: "2026-03-29T09:33:00Z",
    orgName: "Bangladesh Financial Intelligence Unit",
    entityId: "ent-rizwana-phone",
    reasons: [
      {
        rule: "cross_bank_overlap",
        score: 64,
        weight: 6,
        explanation: "Phone identifier appears in four separate STR narratives spanning three banks.",
        evidence: { banks: 3, str_count: 4 },
      },
    ],
  },
];

export const matches: MatchSummary[] = [
  {
    id: "match-001",
    entityId: "ent-rizwana-account",
    matchKey: "1781430000701",
    matchType: "account",
    involvedOrgs: ["Sonali Bank", "BRAC Bank", "Dutch-Bangla Bank"],
    involvedStrIds: ["STR-2604-000112", "STR-2603-009221", "STR-2602-007104"],
    matchCount: 3,
    totalExposure: 22140000,
    riskScore: 92,
    severity: "critical",
    status: "investigating",
  },
  {
    id: "match-002",
    entityId: "ent-rizwana-phone",
    matchKey: "01712xxxxxx",
    matchType: "phone",
    involvedOrgs: ["BRAC Bank", "Islami Bank", "bKash"],
    involvedStrIds: ["STR-2603-009221", "STR-2602-006100", "STR-2601-001918"],
    matchCount: 4,
    totalExposure: 11700000,
    riskScore: 84,
    severity: "high",
    status: "new",
  },
];

export const detectionRuns: DetectionRunSummary[] = [
  { id: "run-001", fileName: "march-retail-scan.csv", status: "completed", alertsGenerated: 18, accountsScanned: 2140, txCount: 40218, createdAt: "2026-04-01T05:10:00Z" },
  { id: "run-002", fileName: "wallet-burst-scan.xlsx", status: "processing", alertsGenerated: 4, accountsScanned: 920, txCount: 11884, createdAt: "2026-04-02T02:30:00Z" },
];

export const cases: CaseSummary[] = [
  {
    id: "case-001",
    caseRef: "KST-2604-00001",
    title: "Rizwana Enterprise network investigation",
    summary: "Multi-bank merchant front with rapid cashout, shared phone aliases, and wallet fan-out.",
    severity: "critical",
    status: "investigating",
    totalExposure: 22140000,
    assignedTo: "Sadia Rahman",
    linkedEntityIds: ["ent-rizwana-account", "ent-rizwana-phone", "ent-bikash-wallet"],
    linkedAlertIds: ["alert-rapid-cashout", "alert-cross-bank"],
    variant: "standard",
  },
];

export const complianceScores: ComplianceScore[] = [
  { orgName: "Sonali Bank", submissionTimeliness: 91, alertConversion: 74, peerCoverage: 88, score: 84 },
  { orgName: "BRAC Bank", submissionTimeliness: 87, alertConversion: 79, peerCoverage: 82, score: 83 },
  { orgName: "Dutch-Bangla Bank", submissionTimeliness: 63, alertConversion: 52, peerCoverage: 70, score: 62 },
];

export const apiKeys: ApiKeySummary[] = [
  { id: "api-001", name: "Case Export Integration", lastUsedAt: "2026-03-31T23:00:00Z", scope: ["reports:write", "cases:read"] },
  { id: "api-002", name: "goAML Sandbox Adapter", lastUsedAt: "2026-03-28T12:40:00Z", scope: ["str:sync", "matches:read"] },
];

export function getViewerForPersona(persona?: string) {
  return demoViewers[persona ?? "bfiu_analyst"] ?? demoViewers.bfiu_analyst;
}

export function searchEntities(query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return entities;
  }
  return entities.filter((entity) =>
    [
      entity.displayValue,
      entity.displayName ?? "",
      entity.entityType,
      entity.canonicalValue,
      entity.tags.join(" "),
    ]
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
}

export function getEntityDossier(entityId: string) {
  return entityDossiers[entityId] ?? entityDossiers["ent-rizwana-account"];
}

export function isoMinutesAgo(minutes: number) {
  return new Date(baseTime - minutes * 60_000).toISOString();
}
