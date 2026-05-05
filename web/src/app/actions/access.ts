"use server";

import { createClient } from "@supabase/supabase-js";

export interface ActionResponse {
  success: boolean;
  message?: string;
}

function getClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    return null;
  }
  return createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

interface BriefingNotificationPayload {
  institution: string;
  institution_type: string;
  designation: string;
  email: string;
  use_case: string;
  submitted_at: string;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function sendBriefingNotification(payload: BriefingNotificationPayload): Promise<void> {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    console.info("access_requests: RESEND_API_KEY not set — skipping notification email.", {
      institution: payload.institution,
    });
    return;
  }

  const to = process.env.BRIEFING_NOTIFY_EMAIL || "intake@enso-intelligence.com";
  const from = process.env.BRIEFING_FROM_EMAIL || "Kestrel <onboarding@resend.dev>";
  const subject = `Kestrel briefing intake · ${payload.institution} (${payload.institution_type})`;

  const text = [
    `A new briefing-intake request has been filed.`,
    ``,
    `Institution:    ${payload.institution}`,
    `Type:           ${payload.institution_type}`,
    `Designation:    ${payload.designation}`,
    `Contact email:  ${payload.email}`,
    `Submitted at:   ${payload.submitted_at}`,
    ``,
    `Intended use:`,
    payload.use_case,
    ``,
    `The full record is in Supabase project bmlyqlkzeuoglyvfythg, table public.access_requests.`,
    `Reply directly to this email to reach the requester.`,
  ].join("\n");

  const html = `
    <div style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; max-width: 640px;">
      <p style="font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #6b7280;">
        ┼ Kestrel · Briefing intake
      </p>
      <h2 style="font-size: 18px; margin: 8px 0 16px 0; color: #111827;">
        ${escapeHtml(payload.institution)} <span style="color:#6b7280;">(${escapeHtml(payload.institution_type)})</span>
      </h2>
      <table style="border-collapse: collapse; font-size: 13px; line-height: 1.6; color: #111827;">
        <tr><td style="padding-right: 16px; color: #6b7280;">Designation</td><td>${escapeHtml(payload.designation)}</td></tr>
        <tr><td style="padding-right: 16px; color: #6b7280;">Contact</td><td><a href="mailto:${escapeHtml(payload.email)}" style="color: #FF3823;">${escapeHtml(payload.email)}</a></td></tr>
        <tr><td style="padding-right: 16px; color: #6b7280;">Submitted</td><td>${escapeHtml(payload.submitted_at)}</td></tr>
      </table>
      <p style="font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #6b7280; margin-top: 24px;">
        Intended use
      </p>
      <p style="white-space: pre-wrap; font-size: 14px; line-height: 1.55; color: #111827;">${escapeHtml(payload.use_case)}</p>
      <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
      <p style="font-size: 11px; color: #6b7280; line-height: 1.55;">
        Full record: Supabase project <code>bmlyqlkzeuoglyvfythg</code>, table <code>public.access_requests</code>.<br />
        Reply directly to this email to reach the requester.
      </p>
    </div>
  `.trim();

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: [to],
        reply_to: payload.email,
        subject,
        text,
        html,
      }),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "<unreadable body>");
      console.error("access_requests: Resend send failed", {
        status: response.status,
        body: body.slice(0, 400),
      });
      return;
    }
    const result = (await response.json().catch(() => null)) as { id?: string } | null;
    console.info("access_requests: notification sent", { resend_id: result?.id });
  } catch (err) {
    console.error("access_requests: Resend network error", { message: (err as Error).message });
  }
}

export async function submitAccessRequest(formData: FormData): Promise<ActionResponse> {
  const institution = formData.get("institution")?.toString().trim();
  const institution_type = formData.get("institution_type")?.toString().trim();
  const designation = formData.get("designation")?.toString().trim();
  const email = formData.get("email")?.toString().trim();
  const use_case = formData.get("use_case")?.toString().trim();

  if (!institution || !institution_type || !designation || !email || !use_case) {
    return { success: false, message: "All fields are required for clearance." };
  }

  if (use_case.length < 50) {
    return { success: false, message: "Intended use must be at least 50 characters for auditing." };
  }

  const supabase = getClient();
  if (!supabase) {
    console.error("access_requests: Supabase env vars missing (NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY).");
    return { success: false, message: "Clearance channel offline. Contact the platform operator directly." };
  }

  const submitted_at = new Date().toISOString();
  const { error } = await supabase.from("access_requests").insert({
    institution,
    institution_type,
    designation,
    email,
    use_case,
  });

  if (error) {
    console.error("access_requests insert failed:", { code: error.code, message: error.message });
    return { success: false, message: "System error logging request. Try again." };
  }

  // Email notification is best-effort: form succeeds even if Resend is unconfigured
  // or the API call fails. The DB row is the source of truth.
  await sendBriefingNotification({
    institution,
    institution_type,
    designation,
    email,
    use_case,
    submitted_at,
  });

  return { success: true };
}
