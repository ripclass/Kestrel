import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const active = url.searchParams.get("active_only");
  const limit = url.searchParams.get("limit");
  if (active) params.set("active_only", active);
  if (limit) params.set("limit", limit);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/status/incidents${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load incidents.") },
      { status: response.status },
    );
  }
  return NextResponse.json({ rows: payload }, { status: response.status });
}

export async function POST(request: Request) {
  const body = await request.text();
  const response = await proxyEngineRequest(`/admin/status/incidents`, {
    method: "POST",
    body: body || "{}",
    headers: { "Content-Type": "application/json" },
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to post incident.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
