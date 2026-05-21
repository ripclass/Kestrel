"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { KestrelMark } from "@/components/common/kestrel-mark";
import { cn } from "@/lib/utils";
import type { OperatorRole } from "@/lib/auth";
import { OPERATOR_NAV_SECTIONS, operatorNavFor } from "@/components/operator/operator-nav";

export interface OperatorIdentity {
  name: string;
  email: string;
  role: OperatorRole;
}

function isActive(pathname: string, href: string): boolean {
  if (pathname === href) return true;
  if (href !== "/platform" && pathname.startsWith(`${href}/`)) return true;
  return false;
}

/** Nav contents — shared by the desktop sidebar and the mobile drawer. */
export function OperatorNav({
  identity,
  onNavigate,
}: {
  identity: OperatorIdentity;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const items = operatorNavFor(identity.role);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--sidebar-border)] px-6 py-6">
        <KestrelMark variant="lockup" size="sm" />
        <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Operator console
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5" aria-label="Operator">
        {OPERATOR_NAV_SECTIONS.map((section) => {
          const sectionItems = items.filter((item) => item.section === section);
          if (sectionItems.length === 0) return null;
          return (
            <div key={section} className="mb-6">
              <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                {section}
              </p>
              <div className="flex flex-col">
                {sectionItems.map((item) => {
                  if (item.planned) {
                    return (
                      <span
                        key={item.href}
                        className="flex items-center justify-between px-3 py-2 font-mono text-[12px] uppercase tracking-[0.14em] text-muted-foreground/50"
                        title="Planned — not yet shipped"
                      >
                        <span>
                          <span aria-hidden className="mr-2">·</span>
                          {item.label}
                        </span>
                        <span className="font-mono text-[9px] tracking-[0.18em]">
                          planned
                        </span>
                      </span>
                    );
                  }
                  const active = isActive(pathname, item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onNavigate}
                      className={cn(
                        "px-3 py-2 font-mono text-[12px] uppercase tracking-[0.14em] transition",
                        active
                          ? "bg-foreground text-background"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <span aria-hidden className={cn("mr-2", active ? "text-background" : "text-accent")}>
                        {active ? "┼" : "·"}
                      </span>
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      <div className="border-t border-[var(--sidebar-border)] px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          Operator
        </p>
        <p className="mt-1 text-sm text-foreground">{identity.name}</p>
        <p className="font-mono text-[11px] text-muted-foreground">{identity.email}</p>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
          {identity.role}
        </p>
      </div>
    </div>
  );
}

export function OperatorSidebar({ identity }: { identity: OperatorIdentity }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] lg:flex">
      <OperatorNav identity={identity} />
    </aside>
  );
}
