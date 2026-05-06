import Link from "next/link";

import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — Press kit and technical documents",
  description:
    "Cross-bank intelligence whitepaper, goAML coverage map, world-class capability matrix, and multi-tenant isolation proof. No registration required.",
};

const documents: {
  tag: string;
  title: string;
  body: string;
  href: string;
  external?: boolean;
}[] = [
  {
    tag: "Doc 01 · Whitepaper",
    title: "Cross-bank intelligence — design and persona isolation.",
    body:
      "How Kestrel resolves entities across institutions, anonymises peer signal for the bank persona, and exposes the full picture to BFIU. Persona invariants backed by unit tests and Postgres RLS.",
    href: "/cross-bank-intelligence",
  },
  {
    tag: "Doc 02 · Coverage map",
    title: "goAML coverage matrix.",
    body:
      "Side-by-side mapping of every goAML screen and workflow against the corresponding Kestrel surface. STR / SAR / CTR / TBML / IER / Catalogue / Disseminations / Match Definitions / Reference Tables / Statistics.",
    href: "/coverage",
  },
  {
    tag: "Doc 03 · Capability matrix",
    title: "World-class capability matrix.",
    body:
      "18 capabilities scored against NICE Actimize, Verafin, Tookitaki, and ComplyAdvantage. 15 at Excellent post-V3, 2 at Partial-with-plan tied to data-soak and first on-prem customer rollout.",
    href: "/capability-matrix",
  },
  {
    tag: "Doc 04 · Isolation proof",
    title: "Multi-tenant isolation, verified.",
    body:
      "Four-layer isolation architecture, verbatim Postgres RLS policy citations, file-level service-guard references, and a live production simulation as a bank CAMLCO showing what they can and cannot see.",
    href: "/multi-tenant-isolation",
  },
];

export default function PressPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
          <div className="max-w-4xl space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Press and partner kit
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              Documents and assets,
              <br />
              <span className="text-landing-muted">without registration.</span>
            </h1>
            <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80">
              The cross-bank intelligence whitepaper, the goAML coverage map, the world-class
              capability matrix, and the multi-tenant isolation proof. Each opens directly on the
              Kestrel surface — no registration, no GitHub bounce. Direct email below for press
              inquiries.
            </p>
          </div>

          <div className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid lg:grid-cols-2 lg:divide-x lg:divide-y-0">
            {documents.slice(0, 2).map((doc) => (
              <DocumentCard key={doc.title} doc={doc} />
            ))}
          </div>
          <div className="grid grid-cols-1 border-x border-b border-landing-rule-solid divide-y divide-landing-rule-solid lg:grid-cols-2 lg:divide-x lg:divide-y-0">
            {documents.slice(2).map((doc) => (
              <DocumentCard key={doc.title} doc={doc} />
            ))}
          </div>

          <div className="mt-12 grid grid-cols-1 gap-12 border border-landing-rule-solid p-8 lg:grid-cols-3 lg:p-10">
            <div className="space-y-3">
              <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                Press contact
              </p>
              <p className="font-landing-body text-sm uppercase tracking-[0.18em] text-landing-foreground">
                Ripon Chowdhury
              </p>
              <p className="font-landing-body text-sm text-landing-foreground/80">
                ripon.chowdhury@kestrelfin.com
              </p>
            </div>
            <div className="space-y-3">
              <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                Issued from
              </p>
              <p className="font-landing-body text-sm uppercase tracking-[0.18em] text-landing-foreground">
                Dhaka, Bangladesh
              </p>
              <p className="font-landing-body text-sm text-landing-foreground/80">
                Enso Intelligence Inc.
              </p>
            </div>
            <div className="space-y-3">
              <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                Live platform
              </p>
              <Link
                href="/signup/bank"
                className="inline-flex items-center gap-2 border border-landing-alarm px-4 py-2 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-alarm transition hover:bg-landing-alarm hover:text-landing-bg"
              >
                Run a pilot →
              </Link>
            </div>
          </div>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}

function DocumentCard({
  doc,
}: {
  doc: { tag: string; title: string; body: string; href: string; external?: boolean };
}) {
  return (
    <article className="flex flex-col gap-6 p-8 lg:p-10">
      <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
        {doc.tag}
      </span>
      <h2 className="font-landing-display text-2xl leading-tight text-landing-foreground">
        {doc.title}
      </h2>
      <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
        {doc.body}
      </p>
      <a
        href={doc.href}
        target={doc.external ? "_blank" : undefined}
        rel={doc.external ? "noreferrer noopener" : undefined}
        className="mt-auto inline-flex items-center gap-2 border-b border-landing-alarm pb-0.5 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground self-start"
      >
        Open document {doc.external ? "↗" : "→"}
      </a>
    </article>
  );
}
