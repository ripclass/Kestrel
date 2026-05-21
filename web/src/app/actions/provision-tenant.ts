"use server";

import { randomBytes } from "node:crypto";

import { createClient } from "@supabase/supabase-js";

import { getCurrentViewer, isPlatformOperatorEmail } from "@/lib/auth";

/**
 * Operator-driven tenant provisioning. Creates an `organizations` row and
 * invites the first admin in one step — the operator-console equivalent of
 * the self-serve `/signup/bank` flow (`bank-signup.ts`), but operator-gated
 * and with operator-chosen org type / plan / classification.
 *
 * Replaces the edit-the-bootstrap-script-and-run-it onboarding path.
 */

const ORG_TYPES = ["bank", "mfs", "nbfi", "regulator"] as const;
const PLAN_IDS = ["starter", "professional", "enterprise", "filing_only"] as const;
const TENANT_KINDS = ["demo", "pilot", "live"] as const;

type OrgType = (typeof ORG_TYPES)[number];
type PlanId = (typeof PLAN_IDS)[number];
type TenantKind = (typeof TENANT_KINDS)[number];

export interface ProvisionTenantInput {
  orgName: string;
  orgType: string;
  planId: string;
  tenantKind: string;
  adminEmail: string;
  adminName: string;
  adminDesignation: string;
  seedDemoData: boolean;
}

export interface ProvisionTenantResponse {
  success: boolean;
  message?: string;
  orgId?: string;
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

function generateOrgSlug(name: string): string {
  const base = slugify(name) || "org";
  return `${base}-${randomBytes(3).toString("hex")}`;
}

export async function provisionTenant(
  input: ProvisionTenantInput,
): Promise<ProvisionTenantResponse> {
  // Operator gate — re-checked here even though the calling page is gated,
  // because a server action is independently reachable.
  const viewer = await getCurrentViewer();
  if (!viewer || !isPlatformOperatorEmail(viewer.email)) {
    return { success: false, message: "Platform-operator access required." };
  }

  const name = input.orgName.trim();
  const adminName = input.adminName.trim();
  const adminEmail = input.adminEmail.trim().toLowerCase();
  const adminDesignation = input.adminDesignation.trim();

  if (name.length < 2) {
    return { success: false, message: "Organization name is required." };
  }
  if (adminName.length < 2) {
    return { success: false, message: "Admin full name is required." };
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail)) {
    return { success: false, message: "A valid admin email is required." };
  }
  if (!ORG_TYPES.includes(input.orgType as OrgType)) {
    return { success: false, message: "Unrecognised organization type." };
  }
  if (!PLAN_IDS.includes(input.planId as PlanId)) {
    return { success: false, message: "Unrecognised plan." };
  }
  if (!TENANT_KINDS.includes(input.tenantKind as TenantKind)) {
    return { success: false, message: "Unrecognised classification." };
  }

  const orgType = input.orgType as OrgType;

  const supabase = getServiceClient();
  if (!supabase) {
    console.error("provision_tenant: Supabase env vars missing.");
    return { success: false, message: "Provisioning channel offline. Check Supabase env." };
  }

  const settings: Record<string, unknown> = {
    tenant_kind: input.tenantKind,
    signup_source: "operator-provisioned",
    provisioned_by: viewer.email,
  };
  if (input.seedDemoData) {
    // Picked up by the demo_bank_seed Beat task within ~10 min.
    settings.demo_seed_pending = true;
  }

  const slug = generateOrgSlug(name);
  const { data: orgRow, error: orgError } = await supabase
    .from("organizations")
    .insert({
      name,
      slug,
      org_type: orgType,
      plan: "trial",
      plan_id: input.planId,
      settings,
    })
    .select("id")
    .single();

  if (orgError || !orgRow) {
    console.error("provision_tenant: org insert failed", orgError?.code, orgError?.message);
    return { success: false, message: "System error creating the workspace. Try again." };
  }

  // Regulator workspaces land on the bfiu_director persona; everything else
  // (bank / mfs / nbfi) is a CAMLCO-style workspace.
  const persona = orgType === "regulator" ? "bfiu_director" : "bank_camlco";
  const siteOrigin = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://kestrelfin.com").replace(
    /\/$/,
    "",
  );

  const { error: inviteError } = await supabase.auth.admin.inviteUserByEmail(adminEmail, {
    data: {
      org_id: orgRow.id,
      full_name: adminName,
      role: "admin",
      persona,
      designation: adminDesignation || "Administrator",
    },
    redirectTo: `${siteOrigin}/overview`,
  });

  if (inviteError) {
    // Roll the org back so a failed invite doesn't leave an orphan tenant.
    await supabase.from("organizations").delete().eq("id", orgRow.id);
    if (/already (registered|been)/i.test(inviteError.message)) {
      return {
        success: false,
        message: "That admin email already has a Kestrel workspace.",
      };
    }
    console.error("provision_tenant: invite failed", inviteError.message);
    return { success: false, message: "Could not send the admin invite. Try again." };
  }

  return { success: true, orgId: orgRow.id };
}
