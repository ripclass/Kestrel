import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { normalizeSTRReportDetail, normalizeSTRReportList } from "@/lib/str-reports";

async function buildResponse(response: Response) {
  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(
    {
      reports: normalizeSTRReportList(payload.reports ?? []),
    },
    { status: response.status },
  );
}

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/str-reports${request.nextUrl.search}`);
  return buildResponse(response);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/str-reports", {
    method: "POST",
    body: JSON.stringify({
      subject_name: body.subjectName,
      subject_account: body.subjectAccount,
      subject_bank: body.subjectBank,
      subject_phone: body.subjectPhone,
      subject_wallet: body.subjectWallet,
      subject_nid: body.subjectNid,
      total_amount: body.totalAmount,
      currency: body.currency,
      transaction_count: body.transactionCount,
      primary_channel: body.primaryChannel,
      category: body.category,
      channels: body.channels,
      date_range_start: body.dateRangeStart || null,
      date_range_end: body.dateRangeEnd || null,
      narrative: body.narrative,
      metadata: body.metadata ?? {},
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json({ report: normalizeSTRReportDetail(payload.report) }, { status: response.status });
}
