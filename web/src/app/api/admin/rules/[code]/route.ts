import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeAdminRule } from "@/lib/admin";
import type { AdminRuleMutationPayload } from "@/types/api";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ code: string }> },
) {
  const { code } = await context.params;
  const body = (await request.json()) as AdminRuleMutationPayload;
  const response = await proxyEngineRequest(`/admin/rules/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify({
      is_active: body.isActive,
      weight: body.weight,
      threshold: Object.prototype.hasOwnProperty.call(body, "threshold") ? body.threshold : undefined,
      description: Object.prototype.hasOwnProperty.call(body, "description") ? body.description : undefined,
    }),
  });
  const payload = await readResponsePayload<{ rule: unknown } | { detail?: string }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update rule configuration.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { rule: normalizeAdminRule((payload as { rule: never }).rule) },
    { status: response.status },
  );
}
