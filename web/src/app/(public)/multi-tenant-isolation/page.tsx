import { MarkdownPage } from "@/components/public/markdown-page";
import { readDocBody } from "@/lib/docs";

export const metadata = {
  title: "Kestrel — Multi-tenant isolation, verified",
  description:
    "Procurement-grade verification that Kestrel's bank-direct tenancy does not leak data across bank tenants and that regulator-only surfaces are not mutable from a bank persona. Verbatim RLS policies, file-level guard citations, and a live production simulation.",
};

export default async function IsolationPage() {
  const body = await readDocBody("multi-tenant-isolation-verified");
  return (
    <MarkdownPage
      eyebrow="Compliance proof"
      title={
        <>
          Multi-tenant isolation.
          <br />
          <span className="text-landing-muted">Verified.</span>
        </>
      }
      subtitle="Four-layer isolation architecture (web route gate → engine route gate → service-layer org-type guard → Postgres RLS), verbatim policy citations, file-and-line guard references, and a live production simulation as a bank CAMLCO showing what they can and cannot see."
      meta={[
        { label: "Document", value: "Doc 04 · Isolation" },
        { label: "Audience", value: "Procurement · Compliance · Audit" },
        { label: "Last updated", value: "2026-05-06" },
        { label: "Companion doc", value: "Cross-bank whitepaper" },
      ]}
      body={body}
    />
  );
}
