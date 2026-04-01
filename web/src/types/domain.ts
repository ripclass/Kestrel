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
  firstSeen: string;
  lastSeen: string;
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
}

export interface CaseSummary {
  id: string;
  caseRef: string;
  title: string;
  summary: string;
  severity: Severity;
  status: CaseStatus;
  totalExposure: number;
  assignedTo: string;
  linkedEntityIds: string[];
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
