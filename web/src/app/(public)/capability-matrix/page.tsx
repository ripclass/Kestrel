import { MarkdownPage } from "@/components/public/markdown-page";
import { readDocBody } from "@/lib/docs";

export const metadata = {
  title: "Kestrel — World-class capability matrix",
  description:
    "Procurement-grade self-assessment of Kestrel against NICE Actimize, Verafin, Tookitaki, and ComplyAdvantage. 18 enterprise capabilities scored, 15 at Excellent post-V3, with each claim backed by a code path or doc artifact.",
};

export default async function CapabilityMatrixPage() {
  const body = await readDocBody("world-class-capability-matrix");
  return (
    <MarkdownPage
      eyebrow="Capability matrix"
      title={
        <>
          18 capabilities.
          <br />
          <span className="text-landing-muted">15 at excellent.</span>
        </>
      }
      subtitle="Where Kestrel sits today against NICE Actimize, Verafin, Tookitaki, and ComplyAdvantage on the 18 enterprise capabilities a procurement reviewer scores. The two remaining Partials are data-soak (sovereign AI corpus) and customer-pull (first on-prem deployment), not engineering work."
      meta={[
        { label: "Document", value: "Doc 03 · Matrix" },
        { label: "Audience", value: "Procurement" },
        { label: "Last updated", value: "2026-05-06" },
        { label: "Snapshot", value: "Post V3 closure" },
      ]}
      body={body}
    />
  );
}
