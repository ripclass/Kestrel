import type {
  AdminIntegration,
  AdminRuleSummary,
  AdminSettings,
  AdminSummary,
  AdminTeamMember,
  AlertDetail,
  AlertSummary,
  CaseWorkspace,
  CaseSummary,
  ComplianceScore,
  Classification,
  DeploymentReadiness,
  DetectionRunDetail,
  DetectionRunSummary,
  DisseminationDetail,
  DisseminationSummary,
  RecipientType,
  FlaggedAccount,
  KpiStat,
  EntityDossier,
  EntitySummary,
  MatchSummary,
  Persona,
  Role,
  ThreatMapRow,
  STRReportDetail,
  STRReportSummary,
  SyntheticBackfillPlan,
  SyntheticBackfillResult,
  TrendPoint,
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

export interface AdminSummaryResponse {
  summary: AdminSummary;
}

export interface AdminSettingsResponse {
  settings: AdminSettings;
}

export interface AdminTeamResponse {
  members: AdminTeamMember[];
}

export interface AdminRulesResponse {
  rules: AdminRuleSummary[];
}

export interface AdminIntegrationsResponse {
  integrations: AdminIntegration[];
}

export interface DeploymentReadinessResponse {
  readiness: DeploymentReadiness | null;
}

export interface AdminRuleMutationPayload {
  isActive?: boolean;
  weight?: number;
  threshold?: number | null;
  description?: string | null;
}

export interface AdminRuleMutationResponse {
  rule: AdminRuleSummary;
}

export interface AdminTeamMutationPayload {
  role?: Role;
  persona?: Persona;
  designation?: string | null;
}

export interface AdminTeamMutationResponse {
  member: AdminTeamMember;
}

export interface SyntheticBackfillPlanResponse {
  plan: SyntheticBackfillPlan;
}

export interface SyntheticBackfillApplyResponse {
  result: SyntheticBackfillResult;
}

export interface LiveOverviewResponse {
  headline: string;
  operational: string[];
  stats: KpiStat[];
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

export interface NationalReportResponse {
  headline: string;
  operational: string[];
  stats: KpiStat[];
  threatMap: ThreatMapRow[];
}

export interface TrendSeriesResponse {
  series: TrendPoint[];
}

export interface ReportExportPayload {
  reportType: string;
}

export interface ReportExportResponse {
  reportType: string;
  status: string;
  message: string;
  generatedAt: string;
}

export interface STRListResponse {
  reports: STRReportSummary[];
}

export interface DisseminationCreatePayload {
  recipientAgency: string;
  recipientType: RecipientType;
  subjectSummary: string;
  linkedReportIds?: string[];
  linkedEntityIds?: string[];
  linkedCaseIds?: string[];
  classification?: Classification;
  metadata?: Record<string, unknown>;
}

export interface DisseminationListResponse {
  disseminations: DisseminationSummary[];
}

export interface DisseminationMutationResponse {
  dissemination: DisseminationDetail;
}

export interface STRMutationResponse {
  report: STRReportDetail;
}

export interface STRDraftPayload {
  reportType?: string;
  subjectName?: string;
  subjectAccount?: string;
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
  supplementsReportId?: string;
  mediaSource?: string;
  mediaUrl?: string;
  mediaPublishedAt?: string;
  ierDirection?: "inbound" | "outbound";
  ierCounterpartyFiu?: string;
  ierCounterpartyCountry?: string;
  ierEgmontRef?: string;
  ierRequestNarrative?: string;
  ierResponseNarrative?: string;
  ierDeadline?: string;
  tbmlInvoiceValue?: number;
  tbmlDeclaredValue?: number;
  tbmlLcReference?: string;
  tbmlHsCode?: string;
  tbmlCommodity?: string;
  tbmlCounterpartyCountry?: string;
}

export interface STRReviewPayload {
  action: "start_review" | "assign" | "flag" | "confirm" | "dismiss";
  note?: string;
  assignedTo?: string;
}

export interface AiExplanationResponse {
  meta: {
    task: string;
    provider: string;
    model: string;
    fallbackUsed: boolean;
  };
  result: {
    summary: string;
    whyItMatters: string;
    recommendedActions: string[];
  };
}

export interface AiStrNarrativePayload {
  subjectName?: string;
  subjectAccount?: string;
  totalAmount?: number;
  category?: string;
  triggerFacts: string[];
}

export interface AiStrNarrativeResponse {
  meta: {
    task: string;
    provider: string;
    model: string;
    fallbackUsed: boolean;
  };
  result: {
    narrative: string;
    missingFields: string[];
    categorySuggestion: string;
    severitySuggestion: string;
  };
}
