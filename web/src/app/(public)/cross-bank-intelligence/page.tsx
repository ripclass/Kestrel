import { MarkdownPage } from "@/components/public/markdown-page";
import { readDocBody } from "@/lib/docs";

export const metadata = {
  title: "Kestrel — Cross-bank intelligence whitepaper",
  description:
    "How Kestrel resolves entities across institutions, anonymises peer signal for the bank persona, and exposes the full picture to BFIU. Persona invariants backed by unit tests and Postgres RLS.",
};

export default async function CrossBankPage() {
  const body = await readDocBody("cross-bank-intelligence");
  return (
    <MarkdownPage
      eyebrow="Whitepaper"
      title={
        <>
          Cross-bank
          <br />
          intelligence.
        </>
      }
      subtitle="The signal no other vendor in Bangladesh has — and the privacy architecture that lets a competitor's CAMLCO trust it. Persona-aware anonymisation enforced before data leaves the engine; cross-institution clusters that BFIU can see whole and a bank can see only its own slice of."
      meta={[
        { label: "Document", value: "Doc 01 · Whitepaper" },
        { label: "Audience", value: "Bank CTO · BFIU · Procurement" },
        { label: "Last updated", value: "2026-05-06" },
        { label: "Verifiable claims", value: "Backed by unit tests + RLS" },
      ]}
      body={body}
    />
  );
}
