"use server";

import { randomBytes } from "node:crypto";

import { createClient } from "@supabase/supabase-js";

import { isBankDirectSignupEnabled } from "@/lib/runtime";

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

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

function generateOrgSlug(bankName: string): string {
  const base = slugify(bankName) || "bank";
  const suffix = randomBytes(3).toString("hex");
  return `${base}-${suffix}`;
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
  return null;
}

export async function submitBankSignup(formData: FormData): Promise<BankSignupResponse> {
  if (!isBankDirectSignupEnabled()) {
    return {
      success: false,
      message: "Self-serve signup is currently closed. File a briefing intake instead.",
    };
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

  const slug = generateOrgSlug(input.bank_name);
  const { data: orgRow, error: orgError } = await supabase
    .from("organizations")
    .insert({
      name: input.bank_name,
      slug,
      org_type: "bank",
      plan: "trial",
      settings: {
        demo_seed_pending: true,
        demo_narrative: input.demo_narrative,
        signup_source: "bank-direct",
      },
    })
    .select("id, slug")
    .single();

  if (orgError || !orgRow) {
    console.error("bank_signup: org insert failed", orgError?.code, orgError?.message);
    return { success: false, message: "System error provisioning workspace. Try again." };
  }

  const siteOrigin = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://kestrel-nine.vercel.app").replace(/\/$/, "");
  const { error: inviteError } = await supabase.auth.admin.inviteUserByEmail(input.email, {
    data: {
      org_id: orgRow.id,
      full_name: input.full_name,
      role: "admin",
      persona: "bank_camlco",
      designation: input.role,
      phone: input.phone || null,
    },
    redirectTo: `${siteOrigin}/overview`,
  });

  if (inviteError) {
    console.error("bank_signup: invite failed", inviteError.message);
    await supabase.from("organizations").delete().eq("id", orgRow.id);
    if (/already (registered|been)/i.test(inviteError.message)) {
      return {
        success: false,
        message: "That email already has a workspace. Sign in or use forgot-password.",
      };
    }
    return { success: false, message: "Could not send invite email. Try again or contact support." };
  }

  return { success: true, email: input.email };
}
