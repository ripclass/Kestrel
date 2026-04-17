import type {
  DiagramDetail,
  DiagramSummary,
  MatchDefinitionDetail,
  MatchDefinitionSummary,
  MatchExecutionSummary,
  SavedQueryDetail,
  SavedQuerySummary,
  SavedQueryType,
} from "@/types/domain";

type RawSavedQuerySummary = {
  id: string;
  org_id: string;
  user_id: string;
  name: string;
  description?: string | null;
  query_type: SavedQueryType;
  is_shared: boolean;
  last_run_at?: string | null;
  run_count: number;
  created_at: string;
  updated_at: string;
};

type RawSavedQueryDetail = RawSavedQuerySummary & {
  query_definition: Record<string, unknown>;
};

type RawDiagramSummary = {
  id: string;
  org_id: string;
  created_by?: string | null;
  title: string;
  description?: string | null;
  linked_case_id?: string | null;
  linked_str_id?: string | null;
  created_at: string;
  updated_at: string;
};

type RawDiagramDetail = RawDiagramSummary & {
  graph_definition: Record<string, unknown>;
};

type RawMatchExecution = {
  id: string;
  definition_id: string;
  executed_at: string;
  executed_by?: string | null;
  hit_count: number;
  execution_status: MatchExecutionSummary["executionStatus"];
  results_summary: Record<string, unknown>;
};

type RawMatchDefinitionSummary = {
  id: string;
  org_id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  last_execution_at?: string | null;
  total_hits: number;
};

type RawMatchDefinitionDetail = RawMatchDefinitionSummary & {
  definition: Record<string, unknown>;
  recent_executions: RawMatchExecution[];
};

export function normalizeSavedQuerySummary(row: RawSavedQuerySummary): SavedQuerySummary {
  return {
    id: row.id,
    orgId: row.org_id,
    userId: row.user_id,
    name: row.name,
    description: row.description,
    queryType: row.query_type,
    isShared: row.is_shared,
    lastRunAt: row.last_run_at,
    runCount: row.run_count,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function normalizeSavedQueryList(rows: RawSavedQuerySummary[]): SavedQuerySummary[] {
  return rows.map(normalizeSavedQuerySummary);
}

export function normalizeSavedQueryDetail(row: RawSavedQueryDetail): SavedQueryDetail {
  return {
    ...normalizeSavedQuerySummary(row),
    queryDefinition: row.query_definition ?? {},
  };
}

export function normalizeDiagramSummary(row: RawDiagramSummary): DiagramSummary {
  return {
    id: row.id,
    orgId: row.org_id,
    createdBy: row.created_by,
    title: row.title,
    description: row.description,
    linkedCaseId: row.linked_case_id,
    linkedStrId: row.linked_str_id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function normalizeDiagramList(rows: RawDiagramSummary[]): DiagramSummary[] {
  return rows.map(normalizeDiagramSummary);
}

export function normalizeDiagramDetail(row: RawDiagramDetail): DiagramDetail {
  return {
    ...normalizeDiagramSummary(row),
    graphDefinition: row.graph_definition ?? {},
  };
}

export function normalizeMatchExecution(row: RawMatchExecution): MatchExecutionSummary {
  return {
    id: row.id,
    definitionId: row.definition_id,
    executedAt: row.executed_at,
    executedBy: row.executed_by,
    hitCount: row.hit_count,
    executionStatus: row.execution_status,
    resultsSummary: row.results_summary ?? {},
  };
}

export function normalizeMatchDefinitionSummary(
  row: RawMatchDefinitionSummary,
): MatchDefinitionSummary {
  return {
    id: row.id,
    orgId: row.org_id,
    name: row.name,
    description: row.description,
    isActive: row.is_active,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    lastExecutionAt: row.last_execution_at,
    totalHits: row.total_hits,
  };
}

export function normalizeMatchDefinitionList(
  rows: RawMatchDefinitionSummary[],
): MatchDefinitionSummary[] {
  return rows.map(normalizeMatchDefinitionSummary);
}

export function normalizeMatchDefinitionDetail(
  row: RawMatchDefinitionDetail,
): MatchDefinitionDetail {
  return {
    ...normalizeMatchDefinitionSummary(row),
    definition: row.definition ?? {},
    recentExecutions: (row.recent_executions ?? []).map(normalizeMatchExecution),
  };
}
