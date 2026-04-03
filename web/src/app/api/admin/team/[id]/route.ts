import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeAdminTeamMember } from "@/lib/admin";
import type { AdminTeamMutationPayload } from "@/types/api";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as AdminTeamMutationPayload;
  const response = await proxyEngineRequest(`/admin/team/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({
      role: body.role,
      persona: body.persona,
      designation: Object.prototype.hasOwnProperty.call(body, "designation") ? body.designation : undefined,
    }),
  });
  const payload = await readResponsePayload<{ member: unknown } | { detail?: string }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update team member.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { member: normalizeAdminTeamMember((payload as { member: never }).member) },
    { status: response.status },
  );
}
