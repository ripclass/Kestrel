import Link from "next/link";

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
    legend: "Omnisearch · entity_type=account preset",
  },
  {
    label: "Person Lookup",
    description: "Search individuals by name or NID.",
    href: "/investigate?type=person",
    legend: "Omnisearch · entity_type=person preset",
  },
  {
    label: "Entity Lookup",
    description: "Find businesses across the shared pool.",
    href: "/investigate?type=business",
    legend: "Omnisearch · entity_type=business preset",
  },
  {
    label: "Address Lookup",
    description: "Find subjects by registered address.",
    href: "/investigate?type=address",
    legend: "pg_trgm over metadata.address",
  },
  {
    label: "Text Lookup",
    description: "Full-text across narratives, notes, descriptions.",
    href: "/investigate?type=text",
    legend: "Same omnisearch, free-form query",
  },
  {
    label: "Quick Finder",
    description: "Unfiltered omnisearch — whatever you type.",
    href: "/investigate",
    legend: "Default /investigate view",
  },
  {
    label: "Transaction Lookup",
    description: "Search transactions by reference, amount, or date.",
    href: "/scan/history",
    legend: "Transactions surface by scan run",
  },
  {
    label: "Report Lookup",
    description: "Any STR/SAR/CTR/IER/TBML/complaint by ref.",
    href: "/strs",
    legend: "Filters every report type from one list",
  },
  {
    label: "Intelligence Report",
    description: "BFIU internal reports and escalated intelligence.",
    href: "/strs?report_type=internal",
    legend: "STR list filtered to report_type=internal",
  },
  {
    label: "Templates",
    description: "Saved queries and narrative templates.",
    href: "/intelligence/saved-queries",
    legend: "Personal + org-shared saved queries",
  },
  {
    label: "Journal",
    description: "Audit trail — every mutation, who did it, when.",
    href: "/admin?section=audit",
    legend: "Admin audit log surface",
  },
  {
    label: "Dissemination",
    description: "Outbound intelligence to LE, regulators, foreign FIUs.",
    href: "/intelligence/disseminations",
    legend: "Full dissemination ledger",
  },
];

export function CatalogueGrid() {
  return (
    <div className="space-y-8">
      <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Each tile is a labelled entry into the same unified search. The goAML vocabulary is preserved;
        Kestrel&apos;s pg_trgm-backed omnisearch handles the actual matching — one index, twelve familiar
        doorways.
      </p>

      <div className="grid gap-0 border border-border sm:grid-cols-2 xl:grid-cols-3">
        {TILES.map((tile, i) => (
          <Link
            key={tile.label}
            href={tile.href}
            title={tile.legend}
            className="group relative flex flex-col gap-3 border-b border-r border-border px-6 py-6 transition hover:bg-foreground/[0.03] [&:nth-child(3n)]:border-r-0 [&:nth-last-child(-n+3)]:border-b-0 sm:[&:nth-child(even)]:border-r-0 sm:[&:nth-child(3n)]:border-r sm:[&:nth-last-child(-n+3)]:border-b xl:[&:nth-last-child(-n+3)]:border-b-0 xl:[&:nth-child(even)]:border-r"
          >
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                {`Tile 0${i + 1 < 10 ? i + 1 : i + 1}`}
              </span>
              <span
                aria-hidden
                className="font-mono text-xs leading-none text-muted-foreground transition group-hover:text-accent"
              >
                ┼
              </span>
            </div>
            <h3 className="font-mono text-base uppercase tracking-[0.12em] text-foreground">
              {tile.label}
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{tile.description}</p>
            <p className="mt-auto pt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground/70">
              {tile.legend}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
