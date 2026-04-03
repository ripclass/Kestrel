import type {
  AlertDetail,
  AlertSummary,
  CaseWorkspace,
  CaseSummary,
  ComplianceScore,
  DetectionRunDetail,
  DetectionRunSummary,
  FlaggedAccount,
  EntityDossier,
  EntitySummary,
  MatchSummary,
  STRReportDetail,
  STRReportSummary,
  TypologySummary,
  Viewer,
} from "@/types/domain";

export interface OverviewResponse {
  viewer: Viewer;
  headline: string;
  kpis: {
    operational: string[];
    stats: {
      label: string;
      value: string;
      delta: string;
      detail: string;
    }[];
  };
}

export interface EntitySearchResponse {
  query: string;
  results: EntitySummary[];
}

export interface EntityDossierResponse {
  entity: EntityDossier;
}

export interface AlertListResponse {
  alerts: AlertSummary[];
}

export interface AlertDetailResponse {
  alert: AlertDetail;
}

export interface AlertMutationPayload {
  action:
    | "start_review"
    | "assign_to_me"
    | "escalate"
    | "mark_true_positive"
    | "mark_false_positive"
    | "create_case";
  note?: string;
  caseTitle?: string;
}

export interface AlertMutationResponse {
  alert: AlertDetail;
  case?: CaseSummary | null;
}

export interface MatchListResponse {
  matches: MatchSummary[];
}

export interface CaseListResponse {
  cases: CaseSummary[];
}

export interface CaseWorkspaceResponse {
  case: CaseWorkspace;
}

export interface CaseMutationPayload {
  action: "add_note" | "assign_to_me" | "update_status";
  note?: string;
  status?:
    | "open"
    | "investigating"
    | "escalated"
    | "pending_action"
    | "closed_confirmed"
    | "closed_false_positive";
}

export interface CaseMutationResponse {
  case: CaseWorkspace;
}

export interface TypologyListResponse {
  typologies: TypologySummary[];
}

export interface DetectionRunListResponse {
  runs: DetectionRunSummary[];
}

export interface DetectionRunDetailResponse {
  run: DetectionRunDetail;
}

export interface DetectionRunResultsResponse {
  results: FlaggedAccount[];
}

export interface ScanQueuePayload {
  fileName?: string;
  selectedRules: string[];
}

export interface ScanQueueResponse {
  run: DetectionRunDetail;
  message: string;
}

export interface ComplianceResponse {
  banks: ComplianceScore[];
}

export interface STRListResponse {
  reports: STRReportSummary[];
}

export interface STRMutationResponse {
  report: STRReportDetail;
}

export interface STRDraftPayload {
  subjectName?: string;
  subjectAccount: string;
  subjectBank?: string;
  subjectPhone?: string;
  subjectWallet?: string;
  subjectNid?: string;
  totalAmount: number;
  currency: string;
  transactionCount: number;
  primaryChannel?: string;
  category: string;
  channels: string[];
  dateRangeStart?: string;
  dateRangeEnd?: string;
  narrative?: string;
  metadata?: Record<string, unknown>;
}

export interface STRReviewPayload {
  action: "start_review" | "assign" | "flag" | "confirm" | "dismiss";
  note?: string;
  assignedTo?: string;
}
