"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { signOutBrowser } from "@/lib/auth-client";

/**
 * Operator-console topbar. Deliberately spare — no universal entity search
 * (operators manage tenants, they do not investigate accounts). Just an
 * Enso-internal marker and sign-out.
 */
export function OperatorTopbar({ email }: { email: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function handleSignOut() {
    setPending(true);
    await signOutBrowser();
    router.push("/login");
    router.refresh();
    setPending(false);
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm">
      <div className="flex items-center justify-between gap-4 pl-16 pr-4 py-4 lg:px-6 xl:px-10">
        <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          <span aria-hidden className="leading-none text-accent">┼</span>
          Enso Intelligence · platform operations
        </span>
        <div className="flex items-center gap-3">
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground sm:inline">
            {email}
          </span>
          <button
            type="button"
            onClick={handleSignOut}
            disabled={pending}
            className="border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background disabled:opacity-50"
          >
            {pending ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </div>
    </header>
  );
}
