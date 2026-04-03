import type { CaseNote, CaseSummary, CaseWorkspace } from "@/types/domain";
import { normalizeEntitySummary, normalizeNetworkGraph } from "@/lib/investigation";

type RawActivityEvent = {
  id: string;
  title: string;
  description: string;
  occurred_at: string;
  actor: string;
};

type RawCaseNote = {
  actor_user_id: string;
  actor_role: string;
  note: string;
  occurred_at: string;
};

type RawEntitySummary = {
  id: string;
  entity_type: string;
  display_value: string;
  display_name?: string | null;
  canonical_value: string;
  risk_score: number;
  severity: CaseSummary["severity"];
  confidence: number;
  status: string;
  report_count: number;
  reporting_orgs: string[];
  total_exposure: number;
  tags: string[];
  first_seen?: string;
  last_seen?: string;
};

type RawCaseSummary = {
  id: string;
  case_ref: string;
  title: string;
  summary: string;
  severity: CaseSummary["severity"];
  status: CaseSummary["status"];
  total_exposure: number;
  assigned_to?: string | null;
  linked_entity_ids: string[];
  linked_alert_ids?: string[];
};

type RawCaseWorkspace = RawCaseSummary & {
  timeline: RawActivityEvent[];
  evidence_entities: RawEntitySummary[];
  notes: RawCaseNote[];
  graph?: Parameters<typeof normalizeNetworkGraph>[0] | null;
};

export function normalizeCaseSummary(item: RawCaseSummary): CaseSummary {
  return {
    id: item.id,
    caseRef: item.case_ref,
    title: item.title,
    summary: item.summary,
    severity: item.severity,
    status: item.status,
    totalExposure: item.total_exposure,
    assignedTo: item.assigned_to ?? undefined,
    linkedEntityIds: item.linked_entity_ids,
    linkedAlertIds: item.linked_alert_ids ?? [],
  };
}

export function normalizeCaseNote(note: RawCaseNote): CaseNote {
  return {
    actorUserId: note.actor_user_id,
    actorRole: note.actor_role,
    note: note.note,
    occurredAt: note.occurred_at,
  };
}

export function normalizeCaseWorkspace(item: RawCaseWorkspace): CaseWorkspace {
  return {
    ...normalizeCaseSummary(item),
    timeline: item.timeline.map((event) => ({
      id: event.id,
      title: event.title,
      description: event.description,
      occurredAt: event.occurred_at,
      actor: event.actor,
    })),
    evidenceEntities: item.evidence_entities.map(normalizeEntitySummary),
    notes: item.notes.map(normalizeCaseNote),
    graph: item.graph ? normalizeNetworkGraph(item.graph) : undefined,
  };
}
