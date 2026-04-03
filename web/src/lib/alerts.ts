import type { AlertDetail, AlertReason, AlertSummary } from "@/types/domain";
import { normalizeEntitySummary, normalizeNetworkGraph } from "@/lib/investigation";

type RawAlertReason = {
  rule: string;
  score: number;
  weight: number;
  explanation: string;
  evidence: Record<string, string | number | boolean>;
  recommended_action?: string | null;
};

type RawEntitySummary = {
  id: string;
  entity_type: string;
  display_value: string;
  display_name?: string | null;
  canonical_value: string;
  risk_score: number;
  severity: AlertSummary["severity"];
  confidence: number;
  status: string;
  report_count: number;
  reporting_orgs: string[];
  total_exposure: number;
  tags: string[];
  first_seen?: string;
  last_seen?: string;
};

type RawAlertSummary = {
  id: string;
  title: string;
  description: string;
  alert_type: string;
  risk_score: number;
  severity: AlertSummary["severity"];
  status: AlertSummary["status"];
  created_at: string;
  org_name: string;
  entity_id: string;
  reasons?: RawAlertReason[];
  assigned_to?: string | null;
  case_id?: string | null;
};

type RawAlertDetail = RawAlertSummary & {
  graph: Parameters<typeof normalizeNetworkGraph>[0];
  entity?: RawEntitySummary | null;
};

export function normalizeAlertReason(reason: RawAlertReason): AlertReason {
  return {
    rule: reason.rule,
    score: reason.score,
    weight: reason.weight,
    explanation: reason.explanation,
    evidence: reason.evidence,
    recommendedAction: reason.recommended_action ?? undefined,
  };
}

export function normalizeAlertSummary(alert: RawAlertSummary): AlertSummary {
  return {
    id: alert.id,
    title: alert.title,
    description: alert.description,
    alertType: alert.alert_type,
    riskScore: alert.risk_score,
    severity: alert.severity,
    status: alert.status,
    createdAt: alert.created_at,
    orgName: alert.org_name,
    entityId: alert.entity_id,
    reasons: (alert.reasons ?? []).map(normalizeAlertReason),
    assignedTo: alert.assigned_to ?? undefined,
    caseId: alert.case_id ?? undefined,
  };
}

export function normalizeAlertDetail(alert: RawAlertDetail): AlertDetail {
  return {
    ...normalizeAlertSummary(alert),
    graph: normalizeNetworkGraph(alert.graph),
    entity: alert.entity ? normalizeEntitySummary(alert.entity) : undefined,
  };
}
