import {
  DocCell,
  DocFinalCta,
  DocMono,
  DocSection,
  DocTable,
  DocTd,
  DocTh,
} from "@/components/public/doc-primitives";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — goAML coverage",
  description:
    "11 report variants supported, goAML XML import and export round-trip, BFIU vocabulary preserved screen-by-screen. Banks keep their existing pipelines unchanged.",
};

const reportVariants: { variant: string; surface: string; notes: string }[] = [
  { variant: "STR", surface: "/str-reports", notes: "First-class lifecycle: draft → submitted → under_review → flagged → confirmed / dismissed. Pipeline runs on every submit (resolve, cross-bank, alert)." },
  { variant: "SAR", surface: "/str-reports", notes: "report_type='sar' variant; same lifecycle as STR." },
  { variant: "CTR", surface: "/str-reports + /cash-transaction-reports", notes: "Single-report variant for ad-hoc CTRs; high-volume bulk CTRs land in a dedicated table." },
  { variant: "TBML", surface: "/str-reports", notes: "Trade-based-money-laundering specific fields: invoice value, declared value, LC reference, HS code, commodity, counterparty country." },
  { variant: "Complaint Report", surface: "/str-reports", notes: "report_type='complaint' variant." },
  { variant: "FIU Escalated Report", surface: "/str-reports", notes: "report_type='escalated' variant." },
  { variant: "Information Exchange Request (IER)", surface: "/iers", notes: "Dedicated Egmont workflow: direction (inbound / outbound), counterparty FIU, Egmont reference, deadline, request and response narratives, respond + close actions." },
  { variant: "Internal Report", surface: "/str-reports", notes: "BFIU-only; report_type='internal' variant." },
  { variant: "Adverse Media-STR", surface: "/str-reports", notes: "Variant with media-provenance fields (media source, URL, published_at)." },
  { variant: "Adverse Media-SAR", surface: "/str-reports", notes: "Same shape, SAR variant." },
  { variant: "Additional Information File", surface: "/str-reports/{id}/supplements", notes: "Supplementary workflow with a parent FK; subject identity auto-inherits from the parent." },
];

export default function GoAmlDocsPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />

      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-5xl px-6 py-20 lg:px-10 lg:py-24">
          <div className="space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Doc 03 · goAML
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              Everything you file today.
              <br />
              <span className="text-landing-muted">Kept exactly as it is.</span>
            </h1>
            <p className="max-w-3xl font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Kestrel takes the goAML XML you already produce and routes it through a modern
              detection and case workflow. No pipeline rewrite. No retraining your CAMLCO on
              vocabulary. The screens still say IER and Catalogue Search and Match Definitions and
              Disseminations, because that&apos;s what BFIU calls them and that&apos;s what you
              know.
            </p>
          </div>

          <dl className="mt-12 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid sm:grid-cols-2 lg:grid-cols-4">
            <DocCell label="Report variants" value="11 supported" />
            <DocCell label="XML round-trip" value="Import + export" />
            <DocCell label="Vocabulary" value="Preserved" />
            <DocCell label="Pipeline rewrite" value="None required" />
          </dl>
        </div>
      </section>

      <DocSection eyebrow="01 · Reports" title="11 report variants. One endpoint family.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Every BFIU report shape lands on the same lifecycle and the same submit pipeline. The{" "}
          <DocMono>report_type</DocMono> column carries the variant; type-specific fields layer on
          top.
        </p>
        <DocTable>
          <thead>
            <tr>
              <DocTh>Report variant</DocTh>
              <DocTh>Surface</DocTh>
              <DocTh>Notes</DocTh>
            </tr>
          </thead>
          <tbody>
            {reportVariants.map((row) => (
              <tr key={row.variant}>
                <DocTd>{row.variant}</DocTd>
                <DocTd>
                  <code className="font-landing-mono text-landing-foreground/90">{row.surface}</code>
                </DocTd>
                <DocTd>{row.notes}</DocTd>
              </tr>
            ))}
          </tbody>
        </DocTable>
      </DocSection>

      <DocSection eyebrow="02 · XML round-trip" title="Import what you have. Export what BFIU needs.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Banks continue emitting goAML-format XML from their existing AML systems and post it
          to <DocMono>POST /str-reports/import-xml</DocMono>. The parser is defensive: extracts
          header + transactions + subjects, maps the goAML{" "}
          <DocMono>submission_code</DocMono> to Kestrel&apos;s <DocMono>report_type</DocMono>,
          ingests transactions tagged with the import batch&apos;s <DocMono>run_id</DocMono>, and
          resolves every subject into the shared entity pool.
        </p>
        <p className="mt-5 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          The export path is the exact inverse:{" "}
          <DocMono>GET /str-reports/{`{id}`}/export.xml</DocMono> emits the primary subject, the
          variant-specific block (<DocMono>ier</DocMono>, <DocMono>tbml</DocMono>, media
          provenance, etc.), and every linked transaction in goAML format. BFIU can hand off a
          Kestrel-resolved STR to a peer FIU or a legacy system without conversion.
        </p>
      </DocSection>

      <DocSection eyebrow="03 · Vocabulary" title="Catalogue Search, IER, Match Definitions, Disseminations.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Every goAML screen name a BFIU analyst learned over the past decade has a corresponding
          surface in Kestrel. The labels are kept; the underlying execution is modern.
        </p>
        <DocTable>
          <thead>
            <tr>
              <DocTh>goAML name</DocTh>
              <DocTh>Kestrel surface</DocTh>
              <DocTh>What changed</DocTh>
            </tr>
          </thead>
          <tbody>
            <tr>
              <DocTd>Catalogue Search (12 lookups)</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/investigate/catalogue</code>
              </DocTd>
              <DocTd>Twelve labelled tiles preserve the goAML rationale; one pg_trgm + ILIKE search powers all of them.</DocTd>
            </tr>
            <tr>
              <DocTd>New Subjects (Account / Person / Entity)</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/intelligence/entities/new</code>
              </DocTd>
              <DocTd>Three tabs with focused fields per type; resolver emits same-owner connections on submit.</DocTd>
            </tr>
            <tr>
              <DocTd>Information Exchange Request (IER)</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/iers</code>
              </DocTd>
              <DocTd>Inbound and outbound tabs, counterparty FIU + Egmont reference, respond and close actions.</DocTd>
            </tr>
            <tr>
              <DocTd>Match Definitions and Executions</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/admin/match-definitions</code>
              </DocTd>
              <DocTd>JSON-DSL custom rules; manager+ can author, toggle, run, or delete; deduped alert emission.</DocTd>
            </tr>
            <tr>
              <DocTd>Disseminations</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/intelligence/disseminations</code>
              </DocTd>
              <DocTd>Disseminate action on every Alert, Case, Entity, and STR; recipient typed; full audit ledger.</DocTd>
            </tr>
            <tr>
              <DocTd>Reference Tables / Lookup Master</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/admin/reference-tables</code>
              </DocTd>
              <DocTd>Banks, branches, countries, channels, categories, currencies, agencies; regulator-only writes.</DocTd>
            </tr>
            <tr>
              <DocTd>Statistics</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/reports/statistics</code>
              </DocTd>
              <DocTd>Recharts dashboards: reports by type by month, by org, CTR volume, dissemination recipients, case outcomes, time-to-review.</DocTd>
            </tr>
            <tr>
              <DocTd>Scheduled Processes</DocTd>
              <DocTd>
                <code className="font-landing-mono text-landing-foreground/90">/admin/schedules</code>
              </DocTd>
              <DocTd>Read-only status view over a Celery Beat schedule pinned to Asia/Dhaka.</DocTd>
            </tr>
          </tbody>
        </DocTable>
      </DocSection>

      <DocFinalCta heading="Run a pilot. Keep your goAML pipeline." />

      <PublicFooter />
    </main>
  );
}
