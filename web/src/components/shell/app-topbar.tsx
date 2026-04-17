"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/common/search-input";
import { DemoPersonaSwitcher } from "@/components/shell/demo-persona-switcher";
import { signOutBrowser } from "@/lib/auth-client";
import type { Viewer } from "@/types/domain";

export function AppTopbar({
  viewer,
  showDemoSwitcher = false,
}: {
  viewer: Viewer;
  showDemoSwitcher?: boolean;
}) {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);

  async function handleSignOut() {
    setIsPending(true);
    await signOutBrowser();
    router.push("/login");
    router.refresh();
    setIsPending(false);
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm">
      <div className="flex flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between xl:px-10">
        <div className="flex flex-1 items-center gap-4">
          <div className="relative max-w-2xl flex-1">
            <SearchInput placeholder="Search account, phone, wallet, NID, or business name" />
          </div>
          <span className="hidden items-center gap-2 border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground lg:inline-flex">
            <span aria-hidden className="leading-none text-accent">┼</span>
            Universal search
          </span>
        </div>
        <div className="flex items-center gap-3">
          {showDemoSwitcher ? (
            <DemoPersonaSwitcher activePersona={viewer.persona} />
          ) : (
            <Button disabled={isPending} variant="outline" onClick={handleSignOut}>
              {isPending ? "Signing out…" : "Sign out"}
            </Button>
          )}
          <button
            type="button"
            aria-label="Notifications"
            className="border border-border bg-card p-2 text-muted-foreground transition hover:border-foreground hover:text-foreground"
          >
            <Bell className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-3 border border-border bg-card px-4 py-2">
            <span
              aria-hidden
              className="flex h-8 w-8 items-center justify-center border border-border bg-background font-mono text-sm uppercase text-foreground"
            >
              {viewer.fullName.charAt(0)}
            </span>
            <div className="hidden text-sm md:block">
              <p className="font-medium text-foreground">{viewer.fullName}</p>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                {viewer.persona.replaceAll("_", " ")}
              </p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
