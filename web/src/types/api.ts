import type {
  AlertSummary,
  CaseSummary,
  ComplianceScore,
  DetectionRunSummary,
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

export interface MatchListResponse {
  matches: MatchSummary[];
}

export interface CaseListResponse {
  cases: CaseSummary[];
}

export interface TypologyListResponse {
  typologies: TypologySummary[];
}

export interface DetectionRunListResponse {
  runs: DetectionRunSummary[];
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
