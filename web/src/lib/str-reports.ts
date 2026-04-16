import type { STRReportDetail, STRReportSummary } from "@/types/domain";

type RawLifecycleEvent = {
  action: string;
  actor_user_id: string;
  actor_role: string;
  actor_org_type: string;
  from_status?: string | null;
  to_status?: string | null;
  note?: string | null;
  occurred_at: string;
};

type RawReviewState = {
  assigned_to?: string | null;
  notes?: {
    actor_user_id: string;
    actor_role: string;
    note: string;
    occurred_at: string;
  }[];
  status_history?: RawLifecycleEvent[];
};

type RawEnrichment = {
  draft_narrative: string;
  missing_fields: string[];
  category_suggestion: string;
  severity_suggestion: string;
  trigger_facts: string[];
  extracted_entities: {
    entity_type: string;
    value: string;
    confidence: number;
  }[];
  generated_at: string;
};

type RawSummary = {
  id: string;
  org_id: string;
  org_name: string;
  report_ref: string;
  report_type?: string;
  status: STRReportSummary["status"];
  subject_name?: string | null;
  subject_account: string;
  subject_bank?: string | null;
  total_amount: number;
  currency: string;
  transaction_count: number;
  primary_channel?: string | null;
  category: string;
  auto_risk_score?: number | null;
  cross_bank_hit: boolean;
  reported_at?: string | null;
  created_at: string;
  updated_at?: string | null;
};

type RawDetail = RawSummary & {
  subject_phone?: string | null;
  subject_wallet?: string | null;
  subject_nid?: string | null;
  channels: string[];
  date_range_start?: string | null;
  date_range_end?: string | null;
  narrative?: string | null;
  matched_entity_ids: string[];
  submitted_by?: string | null;
  reviewed_by?: string | null;
  metadata: Record<string, unknown>;
  enrichment?: RawEnrichment | null;
  review?: RawReviewState | null;
};

function normalizeSummary(report: RawSummary): STRReportSummary {
  return {
    id: report.id,
    orgId: report.org_id,
    orgName: report.org_name,
    reportRef: report.report_ref,
    reportType: (report.report_type ?? "str") as STRReportSummary["reportType"],
    status: report.status,
    subjectName: report.subject_name,
    subjectAccount: report.subject_account,
    subjectBank: report.subject_bank,
    totalAmount: report.total_amount,
    currency: report.currency,
    transactionCount: report.transaction_count,
    primaryChannel: report.primary_channel,
    category: report.category,
    autoRiskScore: report.auto_risk_score,
    crossBankHit: report.cross_bank_hit,
    reportedAt: report.reported_at,
    createdAt: report.created_at,
    updatedAt: report.updated_at,
  };
}

export function normalizeSTRReportDetail(report: RawDetail): STRReportDetail {
  return {
    ...normalizeSummary(report),
    subjectPhone: report.subject_phone,
    subjectWallet: report.subject_wallet,
    subjectNid: report.subject_nid,
    channels: report.channels,
    dateRangeStart: report.date_range_start,
    dateRangeEnd: report.date_range_end,
    narrative: report.narrative,
    matchedEntityIds: report.matched_entity_ids,
    submittedBy: report.submitted_by,
    reviewedBy: report.reviewed_by,
    metadata: report.metadata,
    enrichment: report.enrichment
      ? {
          draftNarrative: report.enrichment.draft_narrative,
          missingFields: report.enrichment.missing_fields,
          categorySuggestion: report.enrichment.category_suggestion,
          severitySuggestion: report.enrichment.severity_suggestion,
          triggerFacts: report.enrichment.trigger_facts,
          extractedEntities: report.enrichment.extracted_entities.map((entity) => ({
            entityType: entity.entity_type,
            value: entity.value,
            confidence: entity.confidence,
          })),
          generatedAt: report.enrichment.generated_at,
        }
      : null,
    review: {
      assignedTo: report.review?.assigned_to,
      notes:
        report.review?.notes?.map((note) => ({
          actorUserId: note.actor_user_id,
          actorRole: note.actor_role,
          note: note.note,
          occurredAt: note.occurred_at,
        })) ?? [],
      statusHistory:
        report.review?.status_history?.map((event) => ({
          action: event.action,
          actorUserId: event.actor_user_id,
          actorRole: event.actor_role,
          actorOrgType: event.actor_org_type,
          fromStatus: event.from_status,
          toStatus: event.to_status,
          note: event.note,
          occurredAt: event.occurred_at,
        })) ?? [],
    },
  };
}

export function normalizeSTRReportList(reports: RawSummary[]): STRReportSummary[] {
  return reports.map(normalizeSummary);
}
