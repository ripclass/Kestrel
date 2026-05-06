import {
  DocCell,
  DocFinalCta,
  DocSection,
} from "@/components/public/doc-primitives";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — Security posture",
  description:
    "Tenancy model, ap-southeast-1 residency, on-prem option, audit logging, AI redaction, BB Circular 26/2024 alignment. Full Postgres policy dump and tenant-isolation simulation available under NDA.",
};

export default function SecurityDocsPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />

      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-5xl px-6 py-20 lg:px-10 lg:py-24">
          <div className="space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Doc 02 · Security
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              How your data
              <br />
              <span className="text-landing-muted">is protected.</span>
            </h1>
            <p className="max-w-3xl font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Per-tenant isolation enforced at the database row, encryption in transit and at
              rest, append-only audit logging, and an AI redaction layer that never lets account
              numbers, NIDs, or phone numbers reach an external model. The mechanisms below are
              live in production today and verifiable on request.
            </p>
          </div>

          <dl className="mt-12 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid sm:grid-cols-2 lg:grid-cols-4">
            <DocCell label="Tenancy" value="Postgres RLS · per-org" />
            <DocCell label="Residency" value="ap-southeast-1" />
            <DocCell label="In transit" value="TLS 1.3" />
            <DocCell label="At rest" value="AES-256" />
          </dl>
        </div>
      </section>

      <DocSection eyebrow="01 · Tenancy" title="Each bank is its own tenant.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Every per-tenant table — accounts, transactions, STR reports, alerts, cases,
          disseminations, customers, screening logs, audit records — is row-level-security
          isolated with a policy of the shape{" "}
          <code className="font-landing-mono text-landing-foreground/90">
            (org_id = auth_org_id()) OR is_regulator()
          </code>
          . A bank user&apos;s session can only ever read the rows tagged with its own org. Cross-
          tenant reads are impossible by construction; service-layer guards add a second line of
          defence on the regulator-only mutation paths. The audit log carries the same isolation
          with no regulator escape hatch.
        </p>
        <p className="mt-5 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          The cross-bank intelligence layer is the single deliberate exception: <em>shared</em>{" "}
          tables hold canonical entity tokens (account number, NID, phone, wallet) and the list of
          orgs that have reported each one. They hold no transactional context. A bank user
          querying them sees peer institutions rendered as &ldquo;Peer institution N&rdquo; and
          match keys redacted to the trailing four characters; only BFIU sees the real labels.
          Persona transformations are applied before data leaves the engine.
        </p>
      </DocSection>

      <DocSection eyebrow="02 · Data residency" title="ap-southeast-1 by default. On-prem on request.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Hosted Kestrel runs on Supabase Postgres in <strong>Singapore (ap-southeast-1)</strong>{" "}
          with the engine on Render in the same region. No data is replicated outside the region.
          The contractual guarantee is one region, full stop — no cross-region failover, no
          analytics warehouse, no third-party data lake.
        </p>
        <p className="mt-5 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Enterprise tier customers can deploy the entire Kestrel stack <strong>inside their own
          data centre</strong>. The same engine image, the same web image, with Postgres + Redis +
          Caddy on a single Docker compose. Air-gapped AI routing skips OpenAI and Anthropic
          entirely; sovereign LLM serving happens against a vLLM endpoint running locally.
          Watchlist refresh runs from operator-supplied source archives instead of live HTTP. The
          on-prem path is ready for a first signed customer to drive.
        </p>
      </DocSection>

      <DocSection eyebrow="03 · Audit log" title="Append-only. Per-org. No regulator override.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Every mutation across the platform writes a row carrying{" "}
          <code className="font-landing-mono text-landing-foreground/90">user_id</code>,{" "}
          <code className="font-landing-mono text-landing-foreground/90">org_id</code>,{" "}
          <code className="font-landing-mono text-landing-foreground/90">action</code>,{" "}
          <code className="font-landing-mono text-landing-foreground/90">resource_type</code>,{" "}
          <code className="font-landing-mono text-landing-foreground/90">resource_id</code>, IP,
          and a request ID that threads through the structured JSON logs. AI invocations log
          provider, model, redaction mode, and digests of the input and output for compliance
          review without storing the content itself. Default retention is 365 days with optional
          archive to encrypted object storage.
        </p>
      </DocSection>

      <DocSection eyebrow="04 · AI safety" title="Redaction before any model. Red-team on every commit.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Account numbers, NIDs, phone numbers, wallet addresses, email addresses, and IP
          addresses are masked before any payload reaches an external model. The redaction layer
          sits between the prompt builder and every provider adapter — there is no path that
          bypasses it. A continuous red-team harness exercises prompt-injection and PII-leak
          regressions on every commit through CI; canary checks fail the build if a model echoes
          an injected instruction or surfaces a raw account number in its output.
        </p>
        <p className="mt-5 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          The platform is built to migrate off external AI entirely. A confidence-routing layer is
          already in place that prefers a sovereign model and falls back to Claude when the
          sovereign confidence is below a per-task threshold. Once a Bangladesh-trained adapter
          clears the promotion harness, traffic flips a percentage at a time with automatic
          rollback if accuracy degrades against the baseline.
        </p>
      </DocSection>

      <DocSection eyebrow="05 · Compliance alignment" title="The frameworks Kestrel was built against.">
        <ul className="mt-6 space-y-3 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85 pl-5 list-disc marker:text-landing-alarm">
          <li>
            <strong>BB Circular 26/2024</strong> — Bangladesh Bank&apos;s digital banking AML
            requirements. Kestrel&apos;s real-time scoring, sanctions screening, KYC re-screening,
            and audit-log retention are designed to the circular&apos;s pipeline expectations.
          </li>
          <li>
            <strong>Money Laundering Prevention Act, 2012</strong> — STR and CTR pipelines, BFIU
            dissemination workflow, audit retention.
          </li>
          <li>
            <strong>Anti-Terrorism Act, 2009</strong> — sanctions enforcement and reporting paths.
          </li>
          <li>
            <strong>FATF Recommendations 9 and 21</strong> — tipping-off prohibitions and
            reporting-entity confidentiality, enforced by the cross-bank persona anonymisation
            layer.
          </li>
          <li>
            <strong>Egmont Group intelligence exchange</strong> — Information Exchange Request
            workflow with counterparty FIU + Egmont reference + deadline, supporting peer-FIU
            handoff in goAML XML.
          </li>
        </ul>
      </DocSection>

      <DocSection eyebrow="06 · Verification" title="Available under NDA on request.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Procurement, audit, and compliance reviewers can request the following under NDA, on a
          two-business-day turnaround:
        </p>
        <ul className="mt-6 space-y-3 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85 pl-5 list-disc marker:text-landing-alarm">
          <li>
            Full <code className="font-landing-mono text-landing-foreground/90">pg_policies</code>{" "}
            dump from the production database, with each policy USING clause verbatim.
          </li>
          <li>
            Tenant-isolation simulation transcript — a production run impersonating a bank CAMLCO
            session and showing what they can and cannot see across every per-tenant table.
          </li>
          <li>
            AI red-team corpus and the most recent CI run results (canary echo + PII leak
            scenarios across all six AI tasks).
          </li>
          <li>The SOC 2 readiness checklist and current gap log.</li>
          <li>Audit-log schema and retention configuration for your tenant.</li>
        </ul>
      </DocSection>

      <DocFinalCta heading="Get the verification pack and brief your CTO." />

      <PublicFooter />
    </main>
  );
}
