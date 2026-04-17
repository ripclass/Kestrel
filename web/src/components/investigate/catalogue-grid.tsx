import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";

type Tile = {
  label: string;
  description: string;
  href: string;
  legend: string;
};

const TILES: Tile[] = [
  {
    label: "Account Lookup",
    description: "Find an account across banks and MFS.",
    href: "/investigate?type=account",
    legend: "Omnisearch with entity_type=account preset.",
  },
  {
    label: "Person Lookup",
    description: "Search individuals by name or NID.",
    href: "/investigate?type=person",
    legend: "Omnisearch with entity_type=person preset.",
  },
  {
    label: "Entity Lookup",
    description: "Find businesses across the shared pool.",
    href: "/investigate?type=business",
    legend: "Omnisearch with entity_type=business preset.",
  },
  {
    label: "Address Lookup",
    description: "Find subjects by registered address.",
    href: "/investigate?type=address",
    legend: "Backed by pg_trgm over metadata.address — free-text.",
  },
  {
    label: "Text Lookup",
    description: "Full-text across narratives, notes, descriptions.",
    href: "/investigate?type=text",
    legend: "Same omnisearch, free-form query.",
  },
  {
    label: "Quick Finder",
    description: "Unfiltered omnisearch — whatever you type.",
    href: "/investigate",
    legend: "The default /investigate view.",
  },
  {
    label: "Transaction Lookup",
    description: "Search transactions by reference, amount, or date.",
    href: "/scan/history",
    legend: "Transactions surface by scan run for now.",
  },
  {
    label: "Report Lookup",
    description: "Find any STR/SAR/CTR/IER/TBML/complaint/etc. by ref.",
    href: "/strs",
    legend: "Filters every report type from one list.",
  },
  {
    label: "Intelligence Report Lookup",
    description: "BFIU internal reports and escalated intelligence.",
    href: "/strs?report_type=internal",
    legend: "Filtered STR list by report_type=internal.",
  },
  {
    label: "Templates Lookup",
    description: "Saved queries and narrative templates.",
    href: "/intelligence/saved-queries",
    legend: "Your personal + org-shared saved queries.",
  },
  {
    label: "Journal Lookup",
    description: "Audit trail — every mutation, who did it, when.",
    href: "/admin?section=audit",
    legend: "Admin audit log surface.",
  },
  {
    label: "Dissemination Lookup",
    description: "Outbound intelligence to law enforcement, regulators, foreign FIUs.",
    href: "/intelligence/disseminations",
    legend: "Full dissemination ledger.",
  },
];

export function CatalogueGrid() {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          Each tile below is a labelled entry into the same unified search. The preset keeps the goAML vocabulary while Kestrel&apos;s
          pg_trgm-backed omnisearch handles the actual matching — one index, twelve familiar doorways.
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {TILES.map((tile) => (
          <Link key={tile.label} href={tile.href} title={tile.legend}>
            <Card className="h-full transition hover:border-primary/40 hover:bg-card">
              <CardContent className="space-y-2 p-5">
                <h3 className="text-base font-semibold">{tile.label}</h3>
                <p className="text-sm text-muted-foreground">{tile.description}</p>
                <p className="text-xs text-muted-foreground/80">{tile.legend}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
