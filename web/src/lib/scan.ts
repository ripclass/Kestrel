import type { DetectionRunDetail, DetectionRunSummary, FlaggedAccount } from "@/types/domain";

type RawFlaggedAccount = {
  entity_id: string;
  account_number: string;
  account_name: string;
  score: number;
  severity: FlaggedAccount["severity"];
  summary: string;
  matched_banks: number;
  total_exposure: number;
  tags?: string[];
  linked_alert_id?: string | null;
  linked_case_id?: string | null;
};

type RawDetectionRunSummary = {
  id: string;
  file_name: string;
  status: DetectionRunSummary["status"];
  alerts_generated: number;
  accounts_scanned: number;
  tx_count: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};

type RawDetectionRunDetail = RawDetectionRunSummary & {
  run_type: string;
  summary: string;
  flagged_accounts?: RawFlaggedAccount[];
  error?: string | null;
};

export function normalizeFlaggedAccount(item: RawFlaggedAccount): FlaggedAccount {
  return {
    entityId: item.entity_id,
    accountNumber: item.account_number,
    accountName: item.account_name,
    score: item.score,
    severity: item.severity,
    summary: item.summary,
    matchedBanks: item.matched_banks,
    totalExposure: item.total_exposure,
    tags: item.tags ?? [],
    linkedAlertId: item.linked_alert_id ?? undefined,
    linkedCaseId: item.linked_case_id ?? undefined,
  };
}

export function normalizeDetectionRunSummary(item: RawDetectionRunSummary): DetectionRunSummary {
  return {
    id: item.id,
    fileName: item.file_name,
    status: item.status,
    alertsGenerated: item.alerts_generated,
    accountsScanned: item.accounts_scanned,
    txCount: item.tx_count,
    createdAt: item.created_at,
    startedAt: item.started_at ?? undefined,
    completedAt: item.completed_at ?? undefined,
  };
}

export function normalizeDetectionRunDetail(item: RawDetectionRunDetail): DetectionRunDetail {
  return {
    ...normalizeDetectionRunSummary(item),
    runType: item.run_type,
    summary: item.summary,
    flaggedAccounts: (item.flagged_accounts ?? []).map(normalizeFlaggedAccount),
    error: item.error ?? undefined,
  };
}
