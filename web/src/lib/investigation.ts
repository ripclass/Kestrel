import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { proxyEngineRequest } from "@/lib/engine-server";
import type {
  EntityDossier,
  EntitySummary,
  MatchSummary,
  NetworkGraph,
} from "@/types/domain";

type RawEntitySummary = {
  id: string;
  entity_type: string;
  display_value: string;
  display_name?: string | null;
  canonical_value: string;
  risk_score: number;
  severity: EntitySummary["severity"];
  confidence: number;
  status: string;
  report_count: number;
  reporting_orgs: string[];
  total_exposure: number;
  tags: string[];
  first_seen?: string;
  last_seen?: string;
};

type RawReportingHistoryItem = {
  org_name: string;
  report_ref: string;
  reported_at: string;
  channel: string;
  amount: number;
};

type RawActivityEvent = {
  id: string;
  title: string;
  description: string;
  occurred_at: string;
  actor: string;
};

type RawNetworkNode = {
  id: string;
  type: NetworkGraph["nodes"][number]["type"];
  label: string;
  subtitle: string;
  risk_score: number;
  severity: NetworkGraph["nodes"][number]["severity"];
};

type RawNetworkEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  relation: string;
  amount?: number | null;
};

type RawNetworkGraph = {
  focus_entity_id: string;
  stats: {
    node_count?: number;
    edge_count?: number;
    max_depth?: number;
    suspicious_paths?: number;
  };
  nodes: RawNetworkNode[];
  edges: RawNetworkEdge[];
};

type RawEntityDossier = RawEntitySummary & {
  narrative: string;
  linked_case_ids: string[];
  linked_alert_ids: string[];
  reporting_history: RawReportingHistoryItem[];
  connections: RawEntitySummary[];
  timeline: RawActivityEvent[];
  graph: RawNetworkGraph;
};

type RawMatchSummary = {
  id: string;
  entity_id: string;
  match_key: string;
  match_type: string;
  involved_orgs: string[];
  involved_str_ids: string[];
  match_count: number;
  total_exposure: number;
  risk_score: number;
  severity: MatchSummary["severity"];
  status: string;
};

export function normalizeNetworkGraph(graph: RawNetworkGraph): NetworkGraph {
  return {
    focusEntityId: graph.focus_entity_id,
    stats: {
      nodeCount: graph.stats.node_count ?? 0,
      edgeCount: graph.stats.edge_count ?? 0,
      maxDepth: graph.stats.max_depth ?? 0,
      suspiciousPaths: graph.stats.suspicious_paths ?? 0,
    },
    nodes: graph.nodes.map((node) => ({
      id: node.id,
      type: node.type,
      label: node.label,
      subtitle: node.subtitle,
      riskScore: node.risk_score,
      severity: node.severity,
    })),
    edges: graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      relation: edge.relation,
      amount: edge.amount ?? undefined,
    })),
  };
}

export function normalizeEntitySummary(entity: RawEntitySummary): EntitySummary {
  return {
    id: entity.id,
    entityType: entity.entity_type,
    displayValue: entity.display_value,
    displayName: entity.display_name ?? undefined,
    canonicalValue: entity.canonical_value,
    riskScore: entity.risk_score,
    severity: entity.severity,
    confidence: entity.confidence,
    status: entity.status,
    reportCount: entity.report_count,
    reportingOrgs: entity.reporting_orgs,
    totalExposure: entity.total_exposure,
    firstSeen: entity.first_seen ?? "",
    lastSeen: entity.last_seen ?? "",
    tags: entity.tags,
  };
}

export function normalizeEntityDossier(entity: RawEntityDossier): EntityDossier {
  return {
    ...normalizeEntitySummary(entity),
    narrative: entity.narrative,
    linkedCaseIds: entity.linked_case_ids,
    linkedAlertIds: entity.linked_alert_ids,
    reportingHistory: entity.reporting_history.map((item) => ({
      orgName: item.org_name,
      reportRef: item.report_ref,
      reportedAt: item.reported_at,
      channel: item.channel,
      amount: item.amount,
    })),
    connections: entity.connections.map(normalizeEntitySummary),
    timeline: entity.timeline.map((event) => ({
      id: event.id,
      title: event.title,
      description: event.description,
      occurredAt: event.occurred_at,
      actor: event.actor,
    })),
    graph: normalizeNetworkGraph(entity.graph),
  };
}

export function normalizeMatchSummary(match: RawMatchSummary): MatchSummary {
  return {
    id: match.id,
    entityId: match.entity_id,
    matchKey: match.match_key,
    matchType: match.match_type,
    involvedOrgs: match.involved_orgs,
    involvedStrIds: match.involved_str_ids,
    matchCount: match.match_count,
    totalExposure: match.total_exposure,
    riskScore: match.risk_score,
    severity: match.severity,
    status: match.status,
  };
}

async function fetchEngineJson<T>(path: string): Promise<T> {
  const response = await proxyEngineRequest(path);
  const payload = await readResponsePayload<T>(response);

  if (!response.ok) {
    throw new Error(detailFromPayload(payload, `Engine request failed for ${path}.`));
  }

  return payload as T;
}

export async function fetchEntitySearch(query = ""): Promise<EntitySummary[]> {
  const params = new URLSearchParams();
  if (query) {
    params.set("query", query);
  }
  const path = `/investigate/search${params.toString() ? `?${params.toString()}` : ""}`;
  const payload = await fetchEngineJson<RawEntitySummary[]>(path);
  return payload.map(normalizeEntitySummary);
}

export async function fetchEntityDossier(entityId: string): Promise<EntityDossier | null> {
  const response = await proxyEngineRequest(`/investigate/entity/${entityId}`);
  const payload = await readResponsePayload<RawEntityDossier>(response);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load entity dossier."));
  }
  return normalizeEntityDossier(payload as RawEntityDossier);
}

export async function fetchNetworkGraph(entityId: string): Promise<NetworkGraph | null> {
  const response = await proxyEngineRequest(`/network/entity/${entityId}`);
  const payload = await readResponsePayload<RawNetworkGraph>(response);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load network graph."));
  }
  return normalizeNetworkGraph(payload as RawNetworkGraph);
}

export async function fetchSharedEntities(query = ""): Promise<EntitySummary[]> {
  const params = new URLSearchParams();
  if (query) {
    params.set("query", query);
  }
  const path = `/intelligence/entities${params.toString() ? `?${params.toString()}` : ""}`;
  const payload = await fetchEngineJson<RawEntitySummary[]>(path);
  return payload.map(normalizeEntitySummary);
}

export async function fetchCrossBankMatches(): Promise<MatchSummary[]> {
  const payload = await fetchEngineJson<RawMatchSummary[]>("/intelligence/matches");
  return payload.map(normalizeMatchSummary);
}
