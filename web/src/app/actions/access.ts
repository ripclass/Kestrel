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

  return { success: true };
}
