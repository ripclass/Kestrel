import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeCaseWorkspace } from "@/lib/cases";
import type { CaseMutationPayload } from "@/types/api";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: Request, { params }: RouteContext) {
  const { id } = await params;
  const body = (await request.json()) as CaseMutationPayload;
  const response = await proxyEngineRequest(`/cases/${id}/actions`, {
    method: "POST",
    body: JSON.stringify({
      action: body.action,
      note: body.note,
      status: body.status,
    }),
  });
  const payload = await readResponsePayload<{ case: unknown }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update case.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { case: normalizeCaseWorkspace((payload as { case: unknown }).case as never) },
    { status: response.status },
  );
}
