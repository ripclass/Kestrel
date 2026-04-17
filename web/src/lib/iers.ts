import type { IERDetail, IERDirection, IERSummary } from "@/types/domain";

type RawSummary = {
  id: string;
  report_ref: string;
  status: string;
  direction: IERDirection;
  counterparty_fiu: string;
  counterparty_country?: string | null;
  egmont_ref?: string | null;
  deadline?: string | null;
  has_response: boolean;
  org_name: string;
  created_at: string;
  updated_at?: string | null;
};

type RawDetail = RawSummary & {
  request_narrative?: string | null;
  response_narrative?: string | null;
  narrative?: string | null;
  linked_entity_ids: string[];
  reported_at?: string | null;
};

export function normalizeIERSummary(row: RawSummary): IERSummary {
  return {
    id: row.id,
    reportRef: row.report_ref,
    status: row.status,
    direction: row.direction,
    counterpartyFiu: row.counterparty_fiu,
    counterpartyCountry: row.counterparty_country,
    egmontRef: row.egmont_ref,
    deadline: row.deadline,
    hasResponse: row.has_response,
    orgName: row.org_name,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function normalizeIERList(rows: RawSummary[]): IERSummary[] {
  return rows.map(normalizeIERSummary);
}

export function normalizeIERDetail(row: RawDetail): IERDetail {
  return {
    ...normalizeIERSummary(row),
    requestNarrative: row.request_narrative,
    responseNarrative: row.response_narrative,
    narrative: row.narrative,
    linkedEntityIds: row.linked_entity_ids ?? [],
    reportedAt: row.reported_at,
  };
}
