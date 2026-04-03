import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { proxyEngineRequest } from "@/lib/engine-server";
import type {
  AdminIntegration,
  AdminRuleSummary,
  AdminSettings,
  AdminSummary,
  AdminTeamMember,
} from "@/types/domain";

type RawAdminSummary = {
  org_name: string;
  org_type: AdminSummary["orgType"];
  plan: string;
  team_members: number;
  active_rules: number;
  total_rules: number;
  api_integrations: number;
  cross_bank_hits: number;
  detection_runs: number;
  synthetic_backfill_available: boolean;
};

type RawAdminSettings = {
  org_name: string;
  org_type: AdminSettings["orgType"];
  plan: string;
  bank_code?: string | null;
  auth_configured: boolean;
  storage_configured: boolean;
  demo_mode_enabled: boolean;
  goaml_sync_enabled: boolean;
  goaml_base_url_configured: boolean;
  environment: string;
  app_version: string;
  uploads_bucket: string;
  exports_bucket: string;
  synthetic_backfill_available: boolean;
};

type RawAdminTeamMember = {
  id: string;
  full_name: string;
  designation?: string | null;
  role: AdminTeamMember["role"];
  persona: AdminTeamMember["persona"];
};

type RawAdminRuleSummary = {
  code: string;
  name: string;
  description: string;
  category: string;
  source: string;
  is_active: boolean;
  is_system: boolean;
  weight: number;
  version: number;
  threshold?: number | null;
};

type RawAdminIntegration = {
  id: string;
  name: string;
  status: string;
  detail: string;
  scope?: string[];
  last_used_at?: string | null;
};

type RawAdminTeamResponse = {
  members?: RawAdminTeamMember[];
};

type RawAdminRulesResponse = {
  rules?: RawAdminRuleSummary[];
};

type RawAdminIntegrationsResponse = {
  integrations?: RawAdminIntegration[];
};

async function fetchEngineJson<T>(path: string): Promise<T> {
  const response = await proxyEngineRequest(path);
  const payload = await readResponsePayload<T>(response);

  if (!response.ok) {
    throw new Error(detailFromPayload(payload, `Engine request failed for ${path}.`));
  }

  return payload as T;
}

export function normalizeAdminSummary(payload: RawAdminSummary): AdminSummary {
  return {
    orgName: payload.org_name,
    orgType: payload.org_type,
    plan: payload.plan,
    teamMembers: payload.team_members,
    activeRules: payload.active_rules,
    totalRules: payload.total_rules,
    apiIntegrations: payload.api_integrations,
    crossBankHits: payload.cross_bank_hits,
    detectionRuns: payload.detection_runs,
    syntheticBackfillAvailable: payload.synthetic_backfill_available,
  };
}

export function normalizeAdminSettings(payload: RawAdminSettings): AdminSettings {
  return {
    orgName: payload.org_name,
    orgType: payload.org_type,
    plan: payload.plan,
    bankCode: payload.bank_code ?? undefined,
    authConfigured: payload.auth_configured,
    storageConfigured: payload.storage_configured,
    demoModeEnabled: payload.demo_mode_enabled,
    goamlSyncEnabled: payload.goaml_sync_enabled,
    goamlBaseUrlConfigured: payload.goaml_base_url_configured,
    environment: payload.environment,
    appVersion: payload.app_version,
    uploadsBucket: payload.uploads_bucket,
    exportsBucket: payload.exports_bucket,
    syntheticBackfillAvailable: payload.synthetic_backfill_available,
  };
}

export function normalizeAdminTeamMember(member: RawAdminTeamMember): AdminTeamMember {
  return {
    id: member.id,
    fullName: member.full_name,
    designation: member.designation ?? undefined,
    role: member.role,
    persona: member.persona,
  };
}

export function normalizeAdminRule(rule: RawAdminRuleSummary): AdminRuleSummary {
  return {
    code: rule.code,
    name: rule.name,
    description: rule.description,
    category: rule.category,
    source: rule.source,
    isActive: rule.is_active,
    isSystem: rule.is_system,
    weight: rule.weight,
    version: rule.version,
    threshold: rule.threshold ?? undefined,
  };
}

export function normalizeAdminIntegration(integration: RawAdminIntegration): AdminIntegration {
  return {
    id: integration.id,
    name: integration.name,
    status: integration.status,
    detail: integration.detail,
    scope: integration.scope ?? [],
    lastUsedAt: integration.last_used_at ?? undefined,
  };
}

export async function fetchAdminSummary(): Promise<AdminSummary> {
  return normalizeAdminSummary(await fetchEngineJson<RawAdminSummary>("/admin/summary"));
}

export async function fetchAdminSettings(): Promise<AdminSettings> {
  return normalizeAdminSettings(await fetchEngineJson<RawAdminSettings>("/admin/settings"));
}

export async function fetchAdminTeam(): Promise<AdminTeamMember[]> {
  const payload = await fetchEngineJson<RawAdminTeamResponse>("/admin/team");
  return (payload.members ?? []).map(normalizeAdminTeamMember);
}

export async function fetchAdminRules(): Promise<AdminRuleSummary[]> {
  const payload = await fetchEngineJson<RawAdminRulesResponse>("/admin/rules");
  return (payload.rules ?? []).map(normalizeAdminRule);
}

export async function fetchAdminIntegrations(): Promise<AdminIntegration[]> {
  const payload = await fetchEngineJson<RawAdminIntegrationsResponse>("/admin/api-keys");
  return (payload.integrations ?? []).map(normalizeAdminIntegration);
}
