import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export async function signOutBrowser() {
  const supabase = createSupabaseBrowserClient();

  if (!supabase) {
    return;
  }

  await supabase.auth.signOut();
}
