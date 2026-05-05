import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const riskLevel = url.searchParams.get("risk_level");
  const kycStatus = url.searchParams.get("kyc_status");
  const limit = url.searchParams.get("limit");
  if (riskLevel) params.set("risk_level", riskLevel);
  if (kycStatus) params.set("kyc_status", kycStatus);
  if (limit) params.set("limit", limit);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/customers${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load customers.") },
      { status: response.status },
    );
  }
  return NextResponse.json({ rows: payload }, { status: response.status });
}

export async function POST(request: Request) {
  const body = await request.text();
  const response = await proxyEngineRequest(`/customers`, {
    method: "POST",
    body: body || "{}",
    headers: { "Content-Type": "application/json" },
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to onboard customer.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
