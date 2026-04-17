import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeSTRReportDetail } from "@/lib/str-reports";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/str-reports/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(normalizeSTRReportDetail(payload as never), { status: response.status });
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/str-reports/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      report_type: body.reportType ?? "str",
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
      supplements_report_id: body.supplementsReportId || null,
      media_source: body.mediaSource || null,
      media_url: body.mediaUrl || null,
      media_published_at: body.mediaPublishedAt || null,
      ier_direction: body.ierDirection || null,
      ier_counterparty_fiu: body.ierCounterpartyFiu || null,
      ier_counterparty_country: body.ierCounterpartyCountry || null,
      ier_egmont_ref: body.ierEgmontRef || null,
      ier_request_narrative: body.ierRequestNarrative || null,
      ier_response_narrative: body.ierResponseNarrative || null,
      ier_deadline: body.ierDeadline || null,
      tbml_invoice_value: body.tbmlInvoiceValue ?? null,
      tbml_declared_value: body.tbmlDeclaredValue ?? null,
      tbml_lc_reference: body.tbmlLcReference || null,
      tbml_hs_code: body.tbmlHsCode || null,
      tbml_commodity: body.tbmlCommodity || null,
      tbml_counterparty_country: body.tbmlCounterpartyCountry || null,
    }),
  });
  const payload = await readResponsePayload<{ report: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const successPayload = payload as { report: unknown };
  return NextResponse.json({ report: normalizeSTRReportDetail(successPayload.report as never) }, { status: response.status });
}
