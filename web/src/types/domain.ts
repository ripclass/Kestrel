export type OrgType = "regulator" | "bank" | "mfs" | "nbfi";
export type Role = "superadmin" | "admin" | "manager" | "analyst" | "viewer";
export type Persona = "bfiu_analyst" | "bank_camlco" | "bfiu_director";
export type Severity = "critical" | "high" | "medium" | "low";
export type AlertStatus =
  | "open"
  | "reviewing"
  | "escalated"
  | "true_positive"
  | "false_positive";
export type CaseStatus =
  | "open"
  | "investigating"
  | "escalated"
  | "pending_action"
  | "closed_confirmed"
  | "closed_false_positive";
export type STRReportStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "flagged"
  | "confirmed"
  | "dismissed";

export interface Viewer {
  id: string;
  email: string;
  fullName: string;
  designation: string;
  role: Role;
  persona: Persona;
  orgId: string;
  orgName: string;
  orgType: OrgType;
}

export interface KpiStat {
  label: string;
  value: string;
  delta: string;
  detail: string;
}

export interface ThreatMapRow {
  channel: string;
  level: string;
  detail: string;
  signalCount: number;
  totalExposure: number;
}

export interface TrendPoint {
  month: string;
  alerts: number;
  strReports: number;
  cases: number;
  scans: number;
}

export interface AlertReason {
  rule: string;
  score: number;
  weight: number;
  explanation: string;
  evidence: Record<string, string | number | boolean>;
  recommendedAction?: string;
}

export interface NetworkNode {
  id: string;
  type: "account" | "phone" | "wallet" | "person" | "business" | "device";
  label: string;
  subtitle: string;
  riskScore: number;
  severity: Severity;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  relation: string;
  amount?: number;
}

export interface NetworkGraph {
  focusEntityId: string;
  stats: {
    nodeCount: number;
    edgeCount: number;
    maxDepth: number;
    suspiciousPaths: number;
  };
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface ActivityEvent {
  id: string;
  title: string;
  description: string;
  occurredAt: string;
  actor: string;
}

export interface ReportingHistoryItem {
  orgName: string;
  reportRef: string;
  reportedAt: string;
  channel: string;
  amount: number;
}

export interface EntitySummary {
  id: string;
  entityType: string;
  displayValue: string;
  displayName?: string;
  canonicalValue: string;
  riskScore: number;
  severity: Severity;
  confidence: number;
  status: string;
  reportCount: number;
  reportingOrgs: string[];
  totalExposure: number;
  firstSeen?: string;
  lastSeen?: string;
  tags: string[];
}

export interface EntityDossier extends EntitySummary {
  narrative: string;
  linkedCaseIds: string[];
  linkedAlertIds: string[];
  reportingHistory: ReportingHistoryItem[];
  connections: EntitySummary[];
  timeline: ActivityEvent[];
  graph: NetworkGraph;
}

export interface AlertSummary {
  id: string;
  title: string;
  description: string;
  alertType: string;
  riskScore: number;
  severity: Severity;
  status: AlertStatus;
  createdAt: string;
  orgName: string;
  entityId: string;
  reasons: AlertReason[];
  assignedTo?: string;
  caseId?: string;
}

export interface AlertDetail extends AlertSummary {
  graph: NetworkGraph;
  entity?: EntitySummary;
}

export interface MatchSummary {
  id: string;
  entityId: string;
  matchKey: string;
  matchType: string;
  involvedOrgs: string[];
  involvedStrIds: string[];
  matchCount: number;
  totalExposure: number;
  riskScore: number;
  severity: Severity;
  status: string;
}

export interface TypologySummary {
  id: string;
  title: string;
  category: string;
  channels: string[];
  indicators: string[];
  narrative: string;
}

export interface DetectionRunSummary {
  id: string;
  fileName: string;
  status: "pending" | "processing" | "completed" | "failed";
  alertsGenerated: number;
  accountsScanned: number;
  txCount: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface FlaggedAccount {
  entityId: string;
  accountNumber: string;
  accountName: string;
  score: number;
  severity: Severity;
  summary: string;
  matchedBanks: number;
  totalExposure: number;
  tags: string[];
  linkedAlertId?: string;
  linkedCaseId?: string;
}

export interface DetectionRunDetail extends DetectionRunSummary {
  runType: string;
  summary: string;
  flaggedAccounts: FlaggedAccount[];
  error?: string;
}

export interface CaseSummary {
  id: string;
  caseRef: string;
  title: string;
  summary: string;
  severity: Severity;
  status: CaseStatus;
  totalExposure: number;
  assignedTo?: string;
  linkedEntityIds: string[];
  linkedAlertIds: string[];
}

export interface CaseNote {
  actorUserId: string;
  actorRole: string;
  note: string;
  occurredAt: string;
}

export interface CaseWorkspace extends CaseSummary {
  timeline: ActivityEvent[];
  evidenceEntities: EntitySummary[];
  notes: CaseNote[];
  graph?: NetworkGraph;
}

export interface ComplianceScore {
  orgName: string;
  submissionTimeliness: number;
  alertConversion: number;
  peerCoverage: number;
  score: number;
}

export interface ApiKeySummary {
  id: string;
  name: string;
  lastUsedAt: string;
  scope: string[];
}

export interface AdminSummary {
  orgName: string;
  orgType: OrgType;
  plan: string;
  teamMembers: number;
  activeRules: number;
  totalRules: number;
  apiIntegrations: number;
  crossBankHits: number;
  detectionRuns: number;
  syntheticBackfillAvailable: boolean;
}

export interface AdminSettings {
  orgName: string;
  orgType: OrgType;
  plan: string;
  bankCode?: string;
  authConfigured: boolean;
  storageConfigured: boolean;
  demoModeEnabled: boolean;
  goamlSyncEnabled: boolean;
  goamlBaseUrlConfigured: boolean;
  environment: string;
  appVersion: string;
  uploadsBucket: string;
  exportsBucket: string;
  syntheticBackfillAvailable: boolean;
}

export interface AdminTeamMember {
  id: string;
  fullName: string;
  designation?: string;
  role: Role;
  persona: Persona;
}

export interface AdminRuleSummary {
  code: string;
  name: string;
  description: string;
  category: string;
  source: string;
  isActive: boolean;
  isSystem: boolean;
  weight: number;
  version: number;
  threshold?: number;
}

export interface AdminIntegration {
  id: string;
  name: string;
  status: string;
  detail: string;
  scope: string[];
  lastUsedAt?: string;
}

export interface SyntheticBackfillPlan {
  datasetRoot: string;
  statements: number;
  entities: number;
  matches: number;
  transactions: number;
  connections: number;
}

export interface SyntheticBackfillResult {
  datasetRoot: string;
  organizations: number;
  entities: number;
  connections: number;
  matches: number;
  transactions: number;
  strReports: number;
  alerts: number;
  cases: number;
  reportingOrgs: Record<string, number>;
}

export interface DeploymentCheck {
  name: string;
  status: string;
  required: boolean;
  detail: string;
  metadata: Record<string, unknown>;
}

export interface DeploymentReadiness {
  status: "ready" | "not_ready";
  version: string;
  environment: string;
  checks: DeploymentCheck[];
}

export interface STRLifecycleEvent {
  action: string;
  actorUserId: string;
  actorRole: string;
  actorOrgType: string;
  fromStatus?: string | null;
  toStatus?: string | null;
  note?: string | null;
  occurredAt: string;
}

export interface STREnrichment {
  draftNarrative: string;
  missingFields: string[];
  categorySuggestion: string;
  severitySuggestion: string;
  triggerFacts: string[];
  extractedEntities: {
    entityType: string;
    value: string;
    confidence: number;
  }[];
  generatedAt: string;
}

export interface STRReviewState {
  assignedTo?: string | null;
  notes: {
    actorUserId: string;
    actorRole: string;
    note: string;
    occurredAt: string;
  }[];
  statusHistory: STRLifecycleEvent[];
}

export interface STRReportSummary {
  id: string;
  orgId: string;
  orgName: string;
  reportRef: string;
  status: STRReportStatus;
  subjectName?: string | null;
  subjectAccount: string;
  subjectBank?: string | null;
  totalAmount: number;
  currency: string;
  transactionCount: number;
  primaryChannel?: string | null;
  category: string;
  autoRiskScore?: number | null;
  crossBankHit: boolean;
  reportedAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
}

export interface STRReportDetail extends STRReportSummary {
  subjectPhone?: string | null;
  subjectWallet?: string | null;
  subjectNid?: string | null;
  channels: string[];
  dateRangeStart?: string | null;
  dateRangeEnd?: string | null;
  narrative?: string | null;
  matchedEntityIds: string[];
  submittedBy?: string | null;
  reviewedBy?: string | null;
  metadata: Record<string, unknown>;
  enrichment?: STREnrichment | null;
  review: STRReviewState;
}
