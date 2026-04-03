import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import type { DeploymentCheck, DeploymentReadiness } from "@/types/domain";

type RawDeploymentCheck = {
  name: string;
  status: string;
  required: boolean;
  detail: string;
  metadata?: Record<string, unknown>;
};

type RawDeploymentReadiness = {
  status: DeploymentReadiness["status"];
  version: string;
  environment: string;
  checks?: RawDeploymentCheck[];
};

function normalizeDeploymentCheck(check: RawDeploymentCheck): DeploymentCheck {
  return {
    name: check.name,
    status: check.status,
    required: check.required,
    detail: check.detail,
    metadata: check.metadata ?? {},
  };
}

function normalizeDeploymentReadiness(payload: RawDeploymentReadiness): DeploymentReadiness {
  return {
    status: payload.status,
    version: payload.version,
    environment: payload.environment,
    checks: (payload.checks ?? []).map(normalizeDeploymentCheck),
  };
}

export async function fetchDeploymentReadiness(): Promise<DeploymentReadiness | null> {
  try {
    const response = await proxyEngineRequest("/ready");
    const payload = await readResponsePayload<RawDeploymentReadiness>(response);
    if (response.status !== 200 && response.status !== 503) {
      return null;
    }
    return normalizeDeploymentReadiness(payload as RawDeploymentReadiness);
  } catch {
    return null;
  }
}
