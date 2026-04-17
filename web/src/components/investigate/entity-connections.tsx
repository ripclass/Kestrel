import Link from "next/link";

import { SeverityPill } from "@/components/common/severity-pill";
import type { EntitySummary } from "@/types/domain";

export function EntityConnections({ entities }: { entities: EntitySummary[] }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Connected entities
        </p>
      </div>
      {entities.length === 0 ? (
        <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          No connections resolved
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {entities.map((entity) => (
            <li key={entity.id}>
              <Link
                href={`/investigate/entity/${entity.id}`}
                className="flex items-start justify-between gap-4 px-6 py-4 transition hover:bg-foreground/[0.03]"
              >
                <div className="space-y-1">
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                    {entity.entityType}
                  </p>
                  <p className="font-mono text-sm text-foreground">{entity.displayValue}</p>
                  {entity.displayName ? (
                    <p className="text-sm leading-relaxed text-muted-foreground">{entity.displayName}</p>
                  ) : null}
                </div>
                <SeverityPill severity={entity.severity} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
