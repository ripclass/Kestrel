import { createSupabaseServerClient } from "@/lib/supabase/server";

function getEngineBaseUrl() {
  const url = process.env.ENGINE_URL ?? process.env.NEXT_PUBLIC_ENGINE_URL;
  if (!url) {
    throw new Error("ENGINE_URL or NEXT_PUBLIC_ENGINE_URL must be configured.");
  }
  return url.replace(/\/$/, "");
}

export async function proxyEngineRequest(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const supabase = await createSupabaseServerClient();
  let accessToken: string | undefined;

  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    accessToken = session?.access_token;
  }

  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(`${getEngineBaseUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}
