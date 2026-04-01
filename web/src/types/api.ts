import type {
  AlertSummary,
  CaseSummary,
  ComplianceScore,
  DetectionRunSummary,
  EntityDossier,
  EntitySummary,
  MatchSummary,
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
