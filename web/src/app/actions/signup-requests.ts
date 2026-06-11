"use server";

import { createClient } from "@supabase/supabase-js";

import { provisionTenant } from "@/app/actions/provision-tenant";
import { getCurrentViewer, isPlatformOperatorEmail } from "@/lib/auth";

/**
 * Operator review of /signup/bank requests (the vetting flow). All three
 * actions re-check the operator gate — server actions are independently
 * reachable. Reads/writes go through the service role; the table is RLS
 * superadmin-only otherwise.
 */

export interface SignupRequestRow {
  id: string;
  bank_name: string;
  full_name: string;
  designation: string;
  email: string;
  phone: string | null;
  demo_narrative: string;
  status: "pending" | "approved" | "rejected";
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  org_id: string | null;
  created_at: string;
}

export interface SignupRequestListResponse {
  success: boolean;
  message?: string;
  requests?: SignupRequestRow[];
}

export interface SignupDecisionResponse {
  success: boolean;
  message?: string;
}

export interface ApproveSignupInput {
  requestId: string;
  planId: string;
  tenantKind: string;
  seedDemoData: boolean;
  note: string;
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

async function requireOperator(): Promise<{ email: string } | null> {
  const viewer = await getCurrentViewer();
  if (!viewer || !isPlatformOperatorEmail(viewer.email)) {
    return null;
  }
  return { email: viewer.email };
}

export async function listSignupRequests(): Promise<SignupRequestListResponse> {
  const operator = await requireOperator();
  if (!operator) {
    return { success: false, message: "Platform-operator access required." };
  }

  const supabase = getServiceClient();
  if (!supabase) {
    return { success: false, message: "Review channel offline. Check Supabase env." };
  }

  const { data, error } = await supabase
    .from("bank_signup_requests")
    .select(
      "id, bank_name, full_name, designation, email, phone, demo_narrative, status, decided_by, decided_at, decision_note, org_id, created_at",
    )
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    console.error("signup_requests: list failed", error.code, error.message);
    return { success: false, message: "Unable to load signup requests." };
  }

  return { success: true, requests: (data ?? []) as SignupRequestRow[] };
}

export async function approveSignupRequest(
  input: ApproveSignupInput,
): Promise<SignupDecisionResponse> {
  const operator = await requireOperator();
  if (!operator) {
    return { success: false, message: "Platform-operator access required." };
  }

  const supabase = getServiceClient();
  if (!supabase) {
    return { success: false, message: "Review channel offline. Check Supabase env." };
  }

  const { data: request, error: loadError } = await supabase
    .from("bank_signup_requests")
    .select("id, bank_name, full_name, designation, email, phone, demo_narrative, status")
    .eq("id", input.requestId)
    .single();

  if (loadError || !request) {
    return { success: false, message: "Request not found." };
  }
  if (request.status !== "pending") {
    return { success: false, message: `Request already ${request.status}.` };
  }

  // provisionTenant re-checks the operator gate, creates the org + admin
  // invite, and rolls the org back if the invite fails.
  const provisioned = await provisionTenant({
    orgName: request.bank_name,
    orgType: "bank",
    planId: input.planId,
    tenantKind: input.tenantKind,
    adminEmail: request.email,
    adminName: request.full_name,
    adminDesignation: request.designation,
    seedDemoData: input.seedDemoData,
    signupRequestId: request.id,
  });

  if (!provisioned.success) {
    return { success: false, message: provisioned.message ?? "Provisioning failed." };
  }

  const { error: updateError } = await supabase
    .from("bank_signup_requests")
    .update({
      status: "approved",
      decided_by: operator.email,
      decided_at: new Date().toISOString(),
      decision_note: input.note.trim() || null,
      org_id: provisioned.orgId ?? null,
    })
    .eq("id", request.id)
    .eq("status", "pending");

  if (updateError) {
    // The tenant exists and the invite went out — surface the bookkeeping
    // failure rather than pretending nothing happened.
    console.error("signup_requests: approve bookkeeping failed", updateError.message);
    return {
      success: true,
      message: "Tenant provisioned and invite sent, but the request row could not be updated — fix it manually.",
    };
  }

  return { success: true };
}

export async function rejectSignupRequest(
  requestId: string,
  note: string,
): Promise<SignupDecisionResponse> {
  const operator = await requireOperator();
  if (!operator) {
    return { success: false, message: "Platform-operator access required." };
  }

  const supabase = getServiceClient();
  if (!supabase) {
    return { success: false, message: "Review channel offline. Check Supabase env." };
  }

  const { data, error } = await supabase
    .from("bank_signup_requests")
    .update({
      status: "rejected",
      decided_by: operator.email,
      decided_at: new Date().toISOString(),
      decision_note: note.trim() || null,
    })
    .eq("id", requestId)
    .eq("status", "pending")
    .select("id");

  if (error) {
    console.error("signup_requests: reject failed", error.message);
    return { success: false, message: "Unable to reject the request." };
  }
  if (!data || data.length === 0) {
    return { success: false, message: "Request not found or already decided." };
  }

  return { success: true };
}
