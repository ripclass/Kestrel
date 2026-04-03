import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeCaseWorkspace } from "@/lib/cases";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/cases/${id}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load case workspace.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { case: normalizeCaseWorkspace(payload as never) },
    { status: response.status },
  );
}
