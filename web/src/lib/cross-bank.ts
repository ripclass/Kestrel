import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type {
  CrossBankEntityRow,
  CrossBankHeatmap,
  CrossBankHeatmapBucket,
  CrossBankMatchView,
  CrossBankSeverityBreakdown,
  CrossBankSummary,
  Severity,
} from "@/types/domain";

type RawSummary = {
  window_days: number;
  entities_flagged_across_banks: number;
  new_this_week: number;
  high_risk_cross_institution: number;
  total_exposure: number;
  cross_bank_alerts_count: number;
  visible_matches_count: number;
  persona_view: "regulator" | "bank";
};

type RawMatchView = {
  id: string;
  entity_id: string;
  match_key: string;
  match_type: string;
  involved_orgs: string[];
  bank_count: number;
  match_count: number;
  total_exposure: number;
  risk_score: number;
  severity: Severity;
  status: string;
  first_seen: string | null;
};

type RawSeverityBreakdown = {
  critical: number;
  high: number;
  medium: number;
  low: number;
};

type RawHeatmapBucket = {
  label: string;
  match_count: number;
  severity_breakdown: RawSeverityBreakdown;
};

type RawHeatmap = {
  window_days: number;
  buckets: RawHeatmapBucket[];
  persona_view: "regulator" | "bank";
};

type RawEntityRow = {
  entity_id: string;
  display: string;
  entity_type: string;
  risk_score: number;
  severity: Severity;
  bank_count: number;
  involved_orgs: string[];
  total_exposure: number;
};

export function normalizeSummary(raw: RawSummary): CrossBankSummary {
  return {
    windowDays: raw.window_days,
    entitiesFlaggedAcrossBanks: raw.entities_flagged_across_banks,
    newThisWeek: raw.new_this_week,
    highRiskCrossInstitution: raw.high_risk_cross_institution,
    totalExposure: raw.total_exposure,
    crossBankAlertsCount: raw.cross_bank_alerts_count,
    visibleMatchesCount: raw.visible_matches_count,
    personaView: raw.persona_view,
  };
}

export function normalizeMatchView(raw: RawMatchView): CrossBankMatchView {
  return {
    id: raw.id,
    entityId: raw.entity_id,
    matchKey: raw.match_key,
    matchType: raw.match_type,
    involvedOrgs: raw.involved_orgs ?? [],
    bankCount: raw.bank_count,
    matchCount: raw.match_count,
    totalExposure: raw.total_exposure,
    riskScore: raw.risk_score,
    severity: raw.severity,
    status: raw.status,
    firstSeen: raw.first_seen,
  };
}

function normalizeSeverityBreakdown(raw: RawSeverityBreakdown): CrossBankSeverityBreakdown {
  return {
    critical: raw.critical ?? 0,
    high: raw.high ?? 0,
    medium: raw.medium ?? 0,
    low: raw.low ?? 0,
  };
}

export function normalizeHeatmapBucket(raw: RawHeatmapBucket): CrossBankHeatmapBucket {
  return {
    label: raw.label,
    matchCount: raw.match_count,
    severityBreakdown: normalizeSeverityBreakdown(raw.severity_breakdown),
  };
}

export function normalizeHeatmap(raw: RawHeatmap): CrossBankHeatmap {
  return {
    windowDays: raw.window_days,
    buckets: (raw.buckets ?? []).map(normalizeHeatmapBucket),
    personaView: raw.persona_view,
  };
}

export function normalizeEntityRow(raw: RawEntityRow): CrossBankEntityRow {
  return {
    entityId: raw.entity_id,
    display: raw.display,
    entityType: raw.entity_type,
    riskScore: raw.risk_score,
    severity: raw.severity,
    bankCount: raw.bank_count,
    involvedOrgs: raw.involved_orgs ?? [],
    totalExposure: raw.total_exposure,
  };
}

export interface CrossBankFilters {
  windowDays?: number;
  severity?: string;
  minBanks?: number;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    usp.set(key, String(value));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchCrossBankSummary(filters: CrossBankFilters = {}): Promise<CrossBankSummary> {
  const qs = buildQuery({ window_days: filters.windowDays });
  const response = await proxyEngineRequest(`/intelligence/cross-bank/summary${qs}`);
  const payload = await readResponsePayload<RawSummary>(response);
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load cross-bank summary."));
  }
  return normalizeSummary(payload as RawSummary);
}

export async function fetchCrossBankMatches(filters: CrossBankFilters = {}): Promise<CrossBankMatchView[]> {
  const qs = buildQuery({
    window_days: filters.windowDays,
    severity: filters.severity,
    min_banks: filters.minBanks,
  });
  const response = await proxyEngineRequest(`/intelligence/cross-bank/matches${qs}`);
  const payload = await readResponsePayload<RawMatchView[]>(response);
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load cross-bank matches."));
  }
  return ((payload as RawMatchView[]) ?? []).map(normalizeMatchView);
}

export async function fetchCrossBankHeatmap(filters: CrossBankFilters = {}): Promise<CrossBankHeatmap> {
  const qs = buildQuery({ window_days: filters.windowDays });
  const response = await proxyEngineRequest(`/intelligence/cross-bank/heatmap${qs}`);
  const payload = await readResponsePayload<RawHeatmap>(response);
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load cross-bank heatmap."));
  }
  return normalizeHeatmap(payload as RawHeatmap);
}

export async function fetchCrossBankTopEntities(
  filters: CrossBankFilters = {},
): Promise<CrossBankEntityRow[]> {
  const qs = buildQuery({ window_days: filters.windowDays });
  const response = await proxyEngineRequest(`/intelligence/cross-bank/top-entities${qs}`);
  const payload = await readResponsePayload<RawEntityRow[]>(response);
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load top cross-bank entities."));
  }
  return ((payload as RawEntityRow[]) ?? []).map(normalizeEntityRow);
}
