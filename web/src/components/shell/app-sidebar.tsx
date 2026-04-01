"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, Workflow } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getNavigation } from "@/components/shell/nav-config";
import type { Viewer } from "@/types/domain";

export function AppSidebar({ viewer }: { viewer: Viewer }) {
  const pathname = usePathname();
  const groups = Object.entries(
    getNavigation(viewer).reduce<Record<string, ReturnType<typeof getNavigation>>>((acc, item) => {
      acc[item.section] ??= [];
      acc[item.section].push(item);
      return acc;
    }, {}),
  );

  return (
    <aside className="hidden w-72 shrink-0 border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] lg:flex lg:flex-col">
      <div className="border-b border-[var(--sidebar-border)] px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-primary/20 p-2 text-primary">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-primary">Kestrel</p>
            <p className="text-sm text-[var(--sidebar-foreground)]/80">{viewer.orgName}</p>
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-8 overflow-y-auto px-4 py-6">
        {groups.map(([section, items]) => (
          <div key={section} className="space-y-3">
            <p className="px-3 text-xs uppercase tracking-[0.2em] text-[var(--sidebar-foreground)]/40">{section}</p>
            <div className="space-y-1">
              {items.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition",
                      active
                        ? "bg-[var(--sidebar-accent)] text-white"
                        : "text-[var(--sidebar-foreground)]/70 hover:bg-white/5 hover:text-white",
                    )}
                  >
                    <span>{item.label}</span>
                    {item.href === "/alerts" ? <Badge className="bg-red-500/20 text-red-200">18</Badge> : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-[var(--sidebar-border)] px-6 py-5">
        <div className="flex items-center gap-3 rounded-2xl bg-white/5 px-4 py-3">
          <Workflow className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-medium">{viewer.fullName}</p>
            <p className="text-xs text-[var(--sidebar-foreground)]/60">{viewer.designation}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
