"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { KestrelMark } from "@/components/common/kestrel-mark";
import { cn } from "@/lib/utils";
import { getNavigation } from "@/components/shell/nav-config";
import { readResponsePayload } from "@/lib/http";
import type { AlertListResponse, CaseListResponse } from "@/types/api";
import type { Viewer } from "@/types/domain";

export function AppSidebar({ viewer }: { viewer: Viewer }) {
  const pathname = usePathname();
  const [counts, setCounts] = useState<{ alerts: number | null; cases: number | null }>({
    alerts: null,
    cases: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    void (async () => {
      try {
        const [alertsResponse, casesResponse] = await Promise.all([
          fetch("/api/alerts", { cache: "no-store", signal: controller.signal }),
          fetch("/api/cases", { cache: "no-store", signal: controller.signal }),
        ]);

        const [alertsPayload, casesPayload] = await Promise.all([
          readResponsePayload<AlertListResponse>(alertsResponse),
          readResponsePayload<CaseListResponse>(casesResponse),
        ]);

        setCounts({
          alerts:
            alertsResponse.ok && "alerts" in alertsPayload && Array.isArray(alertsPayload.alerts)
              ? alertsPayload.alerts.length
              : null,
          cases:
            casesResponse.ok && "cases" in casesPayload && Array.isArray(casesPayload.cases)
              ? casesPayload.cases.length
              : null,
        });
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          return;
        }
        setCounts({ alerts: null, cases: null });
      }
    })();

    return () => controller.abort();
  }, []);

  const groups = Object.entries(
    getNavigation(viewer).reduce<Record<string, ReturnType<typeof getNavigation>>>((acc, item) => {
      acc[item.section] ??= [];
      acc[item.section].push(item);
      return acc;
    }, {}),
  );

  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] lg:flex">
      <div className="border-b border-[var(--sidebar-border)] px-6 py-6">
        <KestrelMark variant="lockup" size="md" />
        <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--sidebar-foreground)]/50">
          {viewer.orgName}
        </p>
      </div>
      <div className="flex-1 space-y-10 overflow-y-auto px-5 py-6">
        {groups.map(([section, items]) => (
          <div key={section} className="space-y-3">
            <p className="px-2 font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--sidebar-foreground)]/40">
              {section}
            </p>
            <div className="space-y-0 border-t border-[var(--sidebar-border)]">
              {items.map((item) => {
                const active = pathname.startsWith(item.href);
                const badgeValue =
                  item.href === "/alerts"
                    ? counts.alerts
                    : item.href === "/cases"
                      ? counts.cases
                      : null;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={item.aka}
                    className={cn(
                      "flex items-center justify-between border-b border-[var(--sidebar-border)] px-3 py-3 text-sm transition",
                      active
                        ? "bg-[var(--sidebar-accent)] text-foreground"
                        : "text-[var(--sidebar-foreground)]/75 hover:bg-[var(--sidebar-accent)]/60 hover:text-foreground",
                    )}
                  >
                    <span className="flex items-center gap-2">
                      {active ? (
                        <span aria-hidden className="font-mono text-[10px] leading-none text-accent">
                          ┼
                        </span>
                      ) : (
                        <span aria-hidden className="w-[1ch] font-mono text-[10px] leading-none text-transparent">
                          ·
                        </span>
                      )}
                      {item.label}
                    </span>
                    {badgeValue !== null ? (
                      <span
                        className={cn(
                          "font-mono text-[10px] tabular-nums",
                          item.href === "/alerts" ? "text-accent" : "text-muted-foreground",
                        )}
                      >
                        {badgeValue.toString().padStart(2, "0")}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-[var(--sidebar-border)] px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--sidebar-foreground)]/40">
          Operator
        </p>
        <p className="mt-2 text-sm text-foreground">{viewer.fullName}</p>
        <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--sidebar-foreground)]/60">
          {viewer.designation}
        </p>
      </div>
    </aside>
  );
}
