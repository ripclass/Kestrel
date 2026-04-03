"use client";

import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { SearchInput } from "@/components/common/search-input";
import { SeverityPill } from "@/components/common/severity-pill";
import { useSearch } from "@/hooks/use-search";

export function Omnisearch() {
  const { query, setQuery, results } = useSearch();

  return (
    <div className="space-y-4">
      <SearchInput
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Type account number, phone, wallet, name, or NID"
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {results.map((entity) => (
          <Link key={entity.id} href={`/investigate/entity/${entity.id}`}>
            <Card className="transition hover:border-primary/40 hover:bg-card">
              <CardContent className="space-y-3 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">{entity.entityType}</p>
                    <h3 className="text-xl font-semibold">{entity.displayValue}</h3>
                    <p className="text-sm text-muted-foreground">{entity.displayName}</p>
                  </div>
                  <SeverityPill severity={entity.severity} />
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{entity.reportCount} reports</span>
                  <span>{entity.reportingOrgs.length} banks</span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      {results.length === 0 ? (
        <p className="text-sm text-muted-foreground">No shared entities matched this query.</p>
      ) : null}
    </div>
  );
}
