import {
  DocCell,
  DocCode,
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
  title: "Kestrel — API integration",
  description:
    "Real-time transaction scoring, sanctions / PEP screening, and KYC onboarding. cURL and Python examples, auth model, decision bands, error envelope, latency SLA, channel allow-list.",
};

export default function ApiDocsPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />

      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-5xl px-6 py-20 lg:px-10 lg:py-24">
          <div className="space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Doc 01 · API integration
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              Real-time decisioning.
              <br />
              <span className="text-landing-muted">One HTTP call.</span>
            </h1>
            <p className="max-w-3xl font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Three endpoints cover the whole integration surface a bank actually needs:
              transaction-level decisioning, sanctions / PEP / adverse-media screening, and KYC
              onboarding. JSON request, JSON response, JWT auth, sub-500ms p99 on the scoring
              path.
            </p>
          </div>

          <dl className="mt-12 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid sm:grid-cols-2 lg:grid-cols-4">
            <DocCell label="Base URL" value="api.kestrelfin.com" />
            <DocCell label="Auth" value="JWT · Bearer" />
            <DocCell label="Latency p99" value="< 500 ms" />
            <DocCell label="OpenAPI" value="GET /docs" />
          </dl>
        </div>
      </section>

      <DocSection eyebrow="01 · Authentication" title="Bearer token from your tenant.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Every request carries a Supabase JWT signed for your bank&apos;s tenant. The engine
          validates HS256 against the shared secret in production and falls back to JWKS for
          rotated keys. Tokens carry the caller&apos;s <DocMono>org_id</DocMono> and{" "}
          <DocMono>persona</DocMono>; row-level security enforces the rest.
        </p>
        <DocCode>{`curl https://api.kestrelfin.com/ready \\
  -H "Authorization: Bearer $KESTREL_TOKEN"`}</DocCode>
      </DocSection>

      <DocSection eyebrow="02 · Real-time scoring" title="POST /transactions/score">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Per-transaction decisioning. Returns a score (0–100), a decision band (approve / review
          / hold / reject), and a reason array your operations team can show on a hold screen.
          Inline sanctions screening fires automatically on either side of the transaction when
          the payload carries a name.
        </p>
        <DocCode>{`curl https://api.kestrelfin.com/transactions/score \\
  -X POST \\
  -H "Authorization: Bearer $KESTREL_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "transaction_external_id": "TXN-2026-04-29-00001",
    "amount": 5500000,
    "currency": "BDT",
    "channel": "BEFTN",
    "from_account_id": "acct_1029",
    "to_account_id":   "acct_5814",
    "from_account_metadata": { "name": "Mohammad Karim", "account_open_days": 12 },
    "to_account_metadata":   { "name": "Padma Trading Ltd" }
  }'`}</DocCode>
        <DocCode>{`{
  "log_id": "9f2b…",
  "score": 78,
  "decision": "hold",
  "confidence": 0.91,
  "reasons": [
    { "code": "amount_very_large",     "weight": 25, "evidence": { "amount_bdt": 5500000 } },
    { "code": "new_account_high_value","weight": 18, "evidence": { "open_days": 12 } },
    { "code": "from_sanctions_hit",    "weight": 35, "evidence": { "list": "OFAC", "match": 0.91 } }
  ],
  "cross_bank_flag": false,
  "latency_ms": 142,
  "request_id": "c0807049-80e3-41d0-a78b-eb7ede8096d2"
}`}</DocCode>
        <p className="mt-6 font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
          Decision bands
        </p>
        <DocTable>
          <thead>
            <tr>
              <DocTh>Score</DocTh>
              <DocTh>Decision</DocTh>
              <DocTh>Bank action</DocTh>
            </tr>
          </thead>
          <tbody>
            <tr>
              <DocTd>0–29</DocTd>
              <DocTd>approve</DocTd>
              <DocTd>release immediately</DocTd>
            </tr>
            <tr>
              <DocTd>30–59</DocTd>
              <DocTd>review</DocTd>
              <DocTd>queue for analyst review post-clearing</DocTd>
            </tr>
            <tr>
              <DocTd>60–79</DocTd>
              <DocTd>hold</DocTd>
              <DocTd>hold pending CAMLCO sign-off</DocTd>
            </tr>
            <tr>
              <DocTd>80–100</DocTd>
              <DocTd>reject</DocTd>
              <DocTd>do not clear; raise STR</DocTd>
            </tr>
          </tbody>
        </DocTable>
      </DocSection>

      <DocSection eyebrow="03 · Sanctions / PEP / Adverse media" title="POST /screening/entity">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Fuzzy match a candidate against a 27,000+ record watchlist pool aggregating OFAC, UN, UK
          FCDO, and BB Domestic, with a ComplyAdvantage adapter for paid PEP and adverse-media
          feeds. Used inline by the scoring endpoint and by the KYC onboarding endpoint;
          available standalone for ad-hoc checks.
        </p>
        <DocCode>{`curl https://api.kestrelfin.com/screening/entity \\
  -X POST \\
  -H "Authorization: Bearer $KESTREL_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Mohammad Karim",
    "date_of_birth": "1978-04-22",
    "nationality": "BD",
    "national_id": "1234567890123",
    "min_score": 0.7,
    "list_sources": ["OFAC", "UN", "UK_OFSI", "BB_DOMESTIC", "PEP"]
  }'`}</DocCode>
      </DocSection>

      <DocSection eyebrow="04 · KYC onboarding" title="POST /customers">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Onboard a customer with inline screening on the primary candidate and every beneficial
          owner. Returns a composed risk score, a decision (low / medium / high / declined), and
          per-party screening hits. A direct primary hit at score ≥ 0.9 forces a decline regardless
          of any other signal — onboarding a sanctioned party is a regulatory violation we don&apos;t
          let through. A periodic re-screening Beat task at 03:00 BDT picks up newly-listed
          parties against the existing customer book and emits Alerts and Cases on new hits.
        </p>
      </DocSection>

      <DocSection eyebrow="05 · Channel allow-list" title="The 12 Bangladesh-relevant rails.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          The <DocMono>channel</DocMono> field on every scoring request must be one of these.
          Anything else returns <DocMono>422</DocMono>.
        </p>
        <ul className="mt-6 grid grid-cols-2 gap-x-6 gap-y-2 font-landing-mono text-[12px] uppercase tracking-[0.06em] text-landing-foreground/85 sm:grid-cols-3 lg:grid-cols-4">
          {[
            "NPSB",
            "BEFTN",
            "RTGS",
            "MFS_BKASH",
            "MFS_NAGAD",
            "MFS_ROCKET",
            "CASH",
            "CHEQUE",
            "CARD",
            "WIRE",
            "LC",
            "DRAFT",
          ].map((c) => (
            <li key={c} className="border border-landing-rule-solid px-3 py-2">
              {c}
            </li>
          ))}
        </ul>
      </DocSection>

      <DocSection eyebrow="06 · Errors" title="Standardised envelope. Every route.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          Non-2xx responses always carry the same shape. Pair the{" "}
          <DocMono>request_id</DocMono> with our structured logs to trace any single call
          end-to-end.
        </p>
        <DocCode>{`{
  "detail": "Insufficient role",
  "request_id": "c0807049-80e3-41d0-a78b-eb7ede8096d2",
  "code": "auth.insufficient_role"
}`}</DocCode>
        <DocTable>
          <thead>
            <tr>
              <DocTh>HTTP</DocTh>
              <DocTh>Meaning</DocTh>
              <DocTh>Typical cause</DocTh>
            </tr>
          </thead>
          <tbody>
            <tr>
              <DocTd>401</DocTd>
              <DocTd>missing / invalid token</DocTd>
              <DocTd>JWT expired, secret rotated, header malformed</DocTd>
            </tr>
            <tr>
              <DocTd>403</DocTd>
              <DocTd>role insufficient</DocTd>
              <DocTd>e.g. bank persona writing a regulator-only resource</DocTd>
            </tr>
            <tr>
              <DocTd>402</DocTd>
              <DocTd>plan does not include feature</DocTd>
              <DocTd>starter tier calling a Professional-only endpoint</DocTd>
            </tr>
            <tr>
              <DocTd>422</DocTd>
              <DocTd>request shape invalid</DocTd>
              <DocTd>missing field, unknown channel, score out of range</DocTd>
            </tr>
            <tr>
              <DocTd>429</DocTd>
              <DocTd>rate limited</DocTd>
              <DocTd>
                retry with exponential backoff; honour <DocMono>Retry-After</DocMono>
              </DocTd>
            </tr>
            <tr>
              <DocTd>500</DocTd>
              <DocTd>engine error</DocTd>
              <DocTd>retry once; if it persists open a ticket with the request_id</DocTd>
            </tr>
          </tbody>
        </DocTable>
      </DocSection>

      <DocSection eyebrow="07 · Spec" title="Authoritative is the live OpenAPI.">
        <p className="mt-4 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85">
          This page covers the three endpoints most banks integrate against. The complete surface
          (130+ routes — STR / SAR / CTR / IER / TBML lifecycle, alerts, cases, agentic
          investigations, dissemination ledger, admin, AI helpers) is auto-generated from the
          engine and lives at{" "}
          <a
            href="https://kestrel-engine.onrender.com/docs"
            className="border-b border-landing-alarm pb-px text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground"
            target="_blank"
            rel="noreferrer noopener"
          >
            kestrel-engine.onrender.com/docs
          </a>
          . Authentication is the same JWT.
        </p>
      </DocSection>

      <DocFinalCta heading="Have your engineers ship from this on a Friday." />

      <PublicFooter />
    </main>
  );
}
