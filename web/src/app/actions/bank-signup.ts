"use server";

import { headers } from "next/headers";

import { createClient } from "@supabase/supabase-js";

import { isBankDirectSignupEnabled } from "@/lib/runtime";

/**
 * Bank-direct signup — vetted flow. Submitting the form no longer provisions
 * a tenant: it files a pending row in `bank_signup_requests` which a platform
 * operator reviews in the operator console (/platform/signups). Approval runs
 * the same provisioning path as console-native tenant creation.
 *
 * Anti-abuse on this surface (it is anonymous and public):
 * - honeypot field — bots that fill it get a fake success and no row
 * - freemail domains rejected — official bank email required
 * - per-IP rate limit (3/hour) backed by the source_ip column
 * - duplicate pending request per email collapses into "already received"
 */

export interface BankSignupResponse {
  success: boolean;
  message?: string;
  email?: string;
}

interface BankSignupInput {
  bank_name: string;
  full_name: string;
  role: string;
  email: string;
  phone: string;
  demo_narrative: string;
}

const FREEMAIL_DOMAINS = new Set([
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "ymail.com",
  "hotmail.com",
  "outlook.com",
  "live.com",
  "msn.com",
  "aol.com",
  "icloud.com",
  "me.com",
  "proton.me",
  "protonmail.com",
  "gmx.com",
  "mail.com",
  "yandex.com",
  "zoho.com",
]);

const MAX_REQUESTS_PER_IP_PER_HOUR = 3;

function getServiceClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    return null;
  }
  return createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function readField(form: FormData, key: string): string {
  return (form.get(key)?.toString() ?? "").trim();
}

function validate(input: BankSignupInput): string | null {
  if (!input.bank_name || input.bank_name.length < 2) return "Bank name is required.";
  if (!input.full_name || input.full_name.length < 2) return "Full name is required.";
  if (!input.role || input.role.length < 2) return "Role is required.";
  if (!input.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email)) {
    return "A valid official email is required.";
  }
  if (input.phone && !/^[+0-9\s\-()]{6,20}$/.test(input.phone)) {
    return "Phone number format is not recognised.";
  }
  if (!input.demo_narrative || input.demo_narrative.length < 30) {
    return "Demo narrative must be at least 30 characters so we can prepare the right walkthrough.";
  }
  const domain = input.email.split("@")[1]?.toLowerCase() ?? "";
  if (FREEMAIL_DOMAINS.has(domain)) {
    return "Use your official bank email address — personal email domains are not accepted. For general enquiries, file a briefing request instead.";
  }
  return null;
}

async function requestOrigin(): Promise<{ ip: string | null; userAgent: string | null }> {
  const hdrs = await headers();
  const forwarded = hdrs.get("x-forwarded-for");
  const ip = forwarded ? forwarded.split(",")[0].trim() : hdrs.get("x-real-ip");
  return { ip: ip || null, userAgent: hdrs.get("user-agent") };
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Best-effort operator notification — the DB row is the source of truth. */
async function sendSignupRequestNotification(input: BankSignupInput): Promise<void> {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    console.info("bank_signup: RESEND_API_KEY not set — skipping notification email.");
    return;
  }

  const to = process.env.BRIEFING_NOTIFY_EMAIL || "intake@enso-intelligence.com";
  const from = process.env.BRIEFING_FROM_EMAIL || "Kestrel <onboarding@resend.dev>";
  const subject = `Kestrel workspace request · ${input.bank_name}`;

  const text = [
    `A new bank workspace request is pending review.`,
    ``,
    `Bank:        ${input.bank_name}`,
    `Contact:     ${input.full_name} (${input.role})`,
    `Email:       ${input.email}`,
    `Phone:       ${input.phone || "—"}`,
    ``,
    `Demo narrative:`,
    input.demo_narrative,
    ``,
    `Review and approve/reject in the operator console: /platform/signups`,
  ].join("\n");

  const html = `
    <div style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace; max-width: 640px;">
      <p style="font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #6b7280;">
        ┼ Kestrel · Workspace request — pending review
      </p>
      <h2 style="font-size: 18px; margin: 8px 0 16px 0; color: #111827;">${escapeHtml(input.bank_name)}</h2>
      <table style="border-collapse: collapse; font-size: 13px; line-height: 1.6; color: #111827;">
        <tr><td style="padding-right: 16px; color: #6b7280;">Contact</td><td>${escapeHtml(input.full_name)} (${escapeHtml(input.role)})</td></tr>
        <tr><td style="padding-right: 16px; color: #6b7280;">Email</td><td><a href="mailto:${escapeHtml(input.email)}" style="color: #FF3823;">${escapeHtml(input.email)}</a></td></tr>
        <tr><td style="padding-right: 16px; color: #6b7280;">Phone</td><td>${escapeHtml(input.phone || "—")}</td></tr>
      </table>
      <p style="font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #6b7280; margin-top: 24px;">
        Demo narrative
      </p>
      <p style="white-space: pre-wrap; font-size: 14px; line-height: 1.55; color: #111827;">${escapeHtml(input.demo_narrative)}</p>
      <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
      <p style="font-size: 11px; color: #6b7280; line-height: 1.55;">
        Review in the operator console at <code>/platform/signups</code>.
        No workspace exists until an operator approves.
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
      body: JSON.stringify({ from, to: [to], reply_to: input.email, subject, text, html }),
    });
    if (!response.ok) {
      const body = await response.text().catch(() => "<unreadable body>");
      console.error(
        `bank_signup: Resend send failed status=${response.status} body=${body.slice(0, 300)}`,
      );
    }
  } catch (err) {
    console.error(`bank_signup: Resend network error message=${(err as Error).message}`);
  }
}

export async function submitBankSignup(formData: FormData): Promise<BankSignupResponse> {
  if (!isBankDirectSignupEnabled()) {
    return {
      success: false,
      message: "Self-serve signup is currently closed. File a briefing intake instead.",
    };
  }

  // Honeypot: real users never see or fill this field. Pretend success so
  // bots get no signal, and write nothing.
  if (readField(formData, "website")) {
    return { success: true, email: readField(formData, "email").toLowerCase() };
  }

  const input: BankSignupInput = {
    bank_name: readField(formData, "bank_name"),
    full_name: readField(formData, "full_name"),
    role: readField(formData, "role"),
    email: readField(formData, "email").toLowerCase(),
    phone: readField(formData, "phone"),
    demo_narrative: readField(formData, "demo_narrative"),
  };

  const validationError = validate(input);
  if (validationError) {
    return { success: false, message: validationError };
  }

  const supabase = getServiceClient();
  if (!supabase) {
    console.error("bank_signup: Supabase env vars missing.");
    return { success: false, message: "Signup channel offline. Contact the platform operator." };
  }

  const { ip, userAgent } = await requestOrigin();

  if (ip) {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const { count, error: rateError } = await supabase
      .from("bank_signup_requests")
      .select("id", { count: "exact", head: true })
      .eq("source_ip", ip)
      .gte("created_at", oneHourAgo);
    if (!rateError && (count ?? 0) >= MAX_REQUESTS_PER_IP_PER_HOUR) {
      return {
        success: false,
        message: "Too many requests from this connection. Try again in an hour, or file a briefing intake.",
      };
    }
  }

  const { data: existing } = await supabase
    .from("bank_signup_requests")
    .select("id")
    .eq("email", input.email)
    .eq("status", "pending")
    .limit(1);
  if (existing && existing.length > 0) {
    return {
      success: true,
      email: input.email,
      message: "A request for this email is already under review.",
    };
  }

  const { error: insertError } = await supabase.from("bank_signup_requests").insert({
    bank_name: input.bank_name,
    full_name: input.full_name,
    designation: input.role,
    email: input.email,
    phone: input.phone || null,
    demo_narrative: input.demo_narrative,
    source_ip: ip,
    user_agent: userAgent,
  });

  if (insertError) {
    console.error("bank_signup: request insert failed", insertError.code, insertError.message);
    return { success: false, message: "System error logging your request. Try again." };
  }

  await sendSignupRequestNotification(input);

  return { success: true, email: input.email };
}
