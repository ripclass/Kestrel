import type { ComplianceScore, KpiStat, ThreatMapRow, TrendPoint } from "@/types/domain";
import type { ComplianceResponse, NationalReportResponse, ReportExportResponse, TrendSeriesResponse } from "@/types/api";

type RawComplianceScore = {
  org_name: string;
  submission_timeliness: number;
  alert_conversion: number;
  peer_coverage: number;
  score: number;
};

type RawThreatMapRow = {
  channel: string;
  level: string;
  detail: string;
  signal_count: number;
  total_exposure: number;
};

type RawTrendPoint = {
  month: string;
  alerts: number;
  str_reports: number;
  cases: number;
  scans: number;
};

type RawNationalReportResponse = {
  headline: string;
  operational?: string[];
  stats?: KpiStat[];
  threat_map?: RawThreatMapRow[];
};

type RawTrendSeriesResponse = {
  series?: RawTrendPoint[];
};

type RawReportExportResponse = {
  report_type: string;
  status: string;
  message: string;
  generated_at: string;
};

export function normalizeComplianceScore(item: RawComplianceScore): ComplianceScore {
  return {
    orgName: item.org_name,
    submissionTimeliness: item.submission_timeliness,
    alertConversion: item.alert_conversion,
    peerCoverage: item.peer_coverage,
    score: item.score,
  };
}

export function normalizeComplianceResponse(items: RawComplianceScore[]): ComplianceResponse {
  return {
    banks: items.map(normalizeComplianceScore),
  };
}

export function normalizeThreatMapRow(item: RawThreatMapRow): ThreatMapRow {
  return {
    channel: item.channel,
    level: item.level,
    detail: item.detail,
    signalCount: item.signal_count,
    totalExposure: item.total_exposure,
  };
}

export function normalizeNationalReportResponse(payload: RawNationalReportResponse): NationalReportResponse {
  return {
    headline: payload.headline,
    operational: payload.operational ?? [],
    stats: payload.stats ?? [],
    threatMap: (payload.threat_map ?? []).map(normalizeThreatMapRow),
  };
}

export function normalizeTrendPoint(point: RawTrendPoint): TrendPoint {
  return {
    month: point.month,
    alerts: point.alerts,
    strReports: point.str_reports,
    cases: point.cases,
    scans: point.scans,
  };
}

export function normalizeTrendSeriesResponse(payload: RawTrendSeriesResponse): TrendSeriesResponse {
  return {
    series: (payload.series ?? []).map(normalizeTrendPoint),
  };
}

export function normalizeReportExportResponse(payload: RawReportExportResponse): ReportExportResponse {
  return {
    reportType: payload.report_type,
    status: payload.status,
    message: payload.message,
    generatedAt: payload.generated_at,
  };
}
