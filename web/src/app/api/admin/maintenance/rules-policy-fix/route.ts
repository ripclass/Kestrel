import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function POST() {
  const response = await proxyEngineRequest("/admin/maintenance/rules-policy-fix", {
    method: "POST",
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to apply rules policy fix.") },
      { status: response.status },
    );
  }

  return NextResponse.json(payload, { status: response.status });
}
