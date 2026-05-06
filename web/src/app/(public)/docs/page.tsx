import Link from "next/link";

import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — Documentation",
  description:
    "Integration guide, security posture, and goAML compatibility. The three documents an integration team and a CTO need before signing.",
};

const docs = [
  {
    tag: "Doc 01 · API",
    title: "Real-time decisioning. One HTTP call.",
    body:
      "POST /transactions/score, /screening/entity, and /customers — auth, request and response shapes, decision bands, error envelope, channel allow-list, latency SLA. cURL and Python examples.",
    href: "/docs/api",
  },
  {
    tag: "Doc 02 · Security",
    title: "How your data is protected.",
    body:
      "Tenancy model, ap-southeast-1 residency, on-prem option, audit logging, AI redaction, BB Circular 26/2024 alignment. Full Postgres policy dump and tenant-isolation simulation available under NDA.",
    href: "/docs/security",
  },
  {
    tag: "Doc 03 · goAML",
    title: "Everything you file today.",
    body:
      "11 report variants supported, goAML XML import and export round-trip, BFIU vocabulary preserved screen-by-screen. Banks keep their existing pipelines unchanged.",
    href: "/docs/goaml",
  },
];

export default function DocsIndex() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
          <div className="max-w-4xl space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Documentation
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              For your integration team
              <br />
              <span className="text-landing-muted">and your CTO.</span>
            </h1>
            <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Three documents. Nothing more. The integration spec your engineers ship from on a
              Friday afternoon, the security posture your CTO signs off on, and the goAML coverage
              answer your CAMLCO needs before a pilot. Everything else lives in the live OpenAPI
              spec at <code className="font-landing-mono text-landing-foreground">/docs</code> on
              the engine.
            </p>
          </div>

          <div className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid lg:grid-cols-3 lg:divide-x lg:divide-y-0">
            {docs.map((doc) => (
              <article key={doc.title} className="flex flex-col gap-6 p-8 lg:p-10">
                <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                  {doc.tag}
                </span>
                <h2 className="font-landing-display text-2xl leading-tight text-landing-foreground">
                  {doc.title}
                </h2>
                <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                  {doc.body}
                </p>
                <Link
                  href={doc.href}
                  className="mt-auto inline-flex items-center gap-2 border-b border-landing-alarm pb-0.5 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground self-start"
                >
                  Open document →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}
