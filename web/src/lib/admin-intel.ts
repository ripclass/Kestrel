import type {
  CaseOutcomeBreakdown,
  CtrVolumeByMonth,
  DisseminationsByAgency,
  OperationalStatistics,
  ReferenceEntry,
  ReferenceTableMeta,
  ReferenceTableName,
  ReportsByOrg,
  ReportsByTypeByMonth,
  ScheduleEntry,
  ScheduleList,
  ScheduleWorker,
  TimeToReviewAverage,
} from "@/types/domain";

type RawReferenceEntry = {
  id: string;
  table_name: ReferenceTableName;
  code: string;
  value: string;
  description?: string | null;
  parent_code?: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type RawReferenceTableMeta = {
  table_name: ReferenceTableName;
  active_count: number;
  total_count: number;
};

type RawStatistics = {
  reports_by_type_by_month: { month: string; report_type: string; count: number }[];
  reports_by_org: { org_name: string; count: number }[];
  ctr_volume_by_month: { month: string; count: number; total_amount: number }[];
  disseminations_by_agency: {
    recipient_agency: string;
    recipient_type: string;
    count: number;
  }[];
  case_outcomes: { status: string; count: number }[];
  time_to_review: { report_type: string; average_hours: number; sample_size: number }[];
  generated_at: string;
};

type RawScheduleEntry = {
  name: string;
  description: string;
  cron: string;
  task: string;
  status: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
};

type RawScheduleWorker = {
  hostname: string;
  alive: boolean;
};

type RawScheduleList = {
  schedules: RawScheduleEntry[];
  workers: RawScheduleWorker[];
  generated_at: string;
};

export function normalizeReferenceEntry(row: RawReferenceEntry): ReferenceEntry {
  return {
    id: row.id,
    tableName: row.table_name,
    code: row.code,
    value: row.value,
    description: row.description,
    parentCode: row.parent_code,
    metadata: row.metadata ?? {},
    isActive: row.is_active,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function normalizeReferenceEntryList(rows: RawReferenceEntry[]): ReferenceEntry[] {
  return rows.map(normalizeReferenceEntry);
}

export function normalizeReferenceTableMeta(
  row: RawReferenceTableMeta,
): ReferenceTableMeta {
  return {
    tableName: row.table_name,
    activeCount: row.active_count,
    totalCount: row.total_count,
  };
}

export function normalizeReferenceTableCounts(
  rows: RawReferenceTableMeta[],
): ReferenceTableMeta[] {
  return rows.map(normalizeReferenceTableMeta);
}

export function normalizeStatistics(payload: RawStatistics): OperationalStatistics {
  const rt: ReportsByTypeByMonth[] = payload.reports_by_type_by_month.map((row) => ({
    month: row.month,
    reportType: row.report_type,
    count: row.count,
  }));
  const byOrg: ReportsByOrg[] = payload.reports_by_org.map((row) => ({
    orgName: row.org_name,
    count: row.count,
  }));
  const ctr: CtrVolumeByMonth[] = payload.ctr_volume_by_month.map((row) => ({
    month: row.month,
    count: row.count,
    totalAmount: row.total_amount,
  }));
  const diss: DisseminationsByAgency[] = payload.disseminations_by_agency.map((row) => ({
    recipientAgency: row.recipient_agency,
    recipientType: row.recipient_type,
    count: row.count,
  }));
  const cases: CaseOutcomeBreakdown[] = payload.case_outcomes.map((row) => ({
    status: row.status,
    count: row.count,
  }));
  const ttr: TimeToReviewAverage[] = payload.time_to_review.map((row) => ({
    reportType: row.report_type,
    averageHours: row.average_hours,
    sampleSize: row.sample_size,
  }));
  return {
    reportsByTypeByMonth: rt,
    reportsByOrg: byOrg,
    ctrVolumeByMonth: ctr,
    disseminationsByAgency: diss,
    caseOutcomes: cases,
    timeToReview: ttr,
    generatedAt: payload.generated_at,
  };
}

export function normalizeScheduleList(payload: RawScheduleList): ScheduleList {
  const schedules: ScheduleEntry[] = payload.schedules.map((row) => ({
    name: row.name,
    description: row.description,
    cron: row.cron,
    task: row.task,
    status: row.status,
    lastRunAt: row.last_run_at,
    nextRunAt: row.next_run_at,
  }));
  const workers: ScheduleWorker[] = payload.workers.map((row) => ({
    hostname: row.hostname,
    alive: row.alive,
  }));
  return {
    schedules,
    workers,
    generatedAt: payload.generated_at,
  };
}
