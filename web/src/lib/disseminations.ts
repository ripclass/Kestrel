import type {
  Classification,
  DisseminationDetail,
  DisseminationSummary,
  RecipientType,
} from "@/types/domain";

type RawSummary = {
  id: string;
  org_id: string;
  org_name: string;
  dissemination_ref: string;
  recipient_agency: string;
  recipient_type: RecipientType;
  subject_summary: string;
  classification: Classification;
  disseminated_by?: string | null;
  disseminated_at: string;
  linked_report_count: number;
  linked_entity_count: number;
  linked_case_count: number;
  created_at: string;
};

type RawDetail = RawSummary & {
  linked_report_ids: string[];
  linked_entity_ids: string[];
  linked_case_ids: string[];
  metadata: Record<string, unknown>;
};

function normalizeSummary(row: RawSummary): DisseminationSummary {
  return {
    id: row.id,
    orgId: row.org_id,
    orgName: row.org_name,
    disseminationRef: row.dissemination_ref,
    recipientAgency: row.recipient_agency,
    recipientType: row.recipient_type,
    subjectSummary: row.subject_summary,
    classification: row.classification,
    disseminatedBy: row.disseminated_by,
    disseminatedAt: row.disseminated_at,
    linkedReportCount: row.linked_report_count,
    linkedEntityCount: row.linked_entity_count,
    linkedCaseCount: row.linked_case_count,
    createdAt: row.created_at,
  };
}

export function normalizeDisseminationSummary(row: RawSummary): DisseminationSummary {
  return normalizeSummary(row);
}

export function normalizeDisseminationList(rows: RawSummary[]): DisseminationSummary[] {
  return rows.map(normalizeSummary);
}

export function normalizeDisseminationDetail(row: RawDetail): DisseminationDetail {
  return {
    ...normalizeSummary(row),
    linkedReportIds: row.linked_report_ids ?? [],
    linkedEntityIds: row.linked_entity_ids ?? [],
    linkedCaseIds: row.linked_case_ids ?? [],
    metadata: row.metadata ?? {},
  };
}
