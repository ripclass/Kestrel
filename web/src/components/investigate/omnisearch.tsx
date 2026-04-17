"use client";

import Link from "next/link";

import { SearchInput } from "@/components/common/search-input";
import { SeverityPill } from "@/components/common/severity-pill";
import { useSearch } from "@/hooks/use-search";

export function Omnisearch() {
  const { query, setQuery, results } = useSearch();

  return (
    <div className="space-y-6">
      <SearchInput
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Type account number, phone, wallet, name, or NID"
      />
      {results.length === 0 ? (
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          No shared entities matched this query
        </p>
      ) : (
        <div className="border border-border divide-y divide-border">
          {results.map((entity) => (
            <Link
              key={entity.id}
              href={`/investigate/entity/${entity.id}`}
              className="grid grid-cols-[1fr_auto] items-start gap-6 px-5 py-4 transition hover:bg-foreground/[0.03]"
            >
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  {entity.entityType}
                </p>
                <p className="font-mono text-base text-foreground">{entity.displayValue}</p>
                {entity.displayName ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">{entity.displayName}</p>
                ) : null}
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  <span className="tabular-nums">{entity.reportCount}</span> reports ·{" "}
                  <span className="tabular-nums">{entity.reportingOrgs.length}</span> banks
                </p>
              </div>
              <SeverityPill severity={entity.severity} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
