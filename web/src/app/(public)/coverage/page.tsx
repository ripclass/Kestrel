import { MarkdownPage } from "@/components/public/markdown-page";
import { readDocBody } from "@/lib/docs";

export const metadata = {
  title: "Kestrel — goAML coverage map",
  description:
    "Side-by-side mapping of every goAML capability against the corresponding Kestrel surface. STR / SAR / CTR / TBML / IER / Catalogue / Match Definitions / Disseminations / Reference Tables / Statistics, plus the capabilities Kestrel adds beyond goAML.",
};

export default async function CoveragePage() {
  const body = await readDocBody("goaml-coverage");
  return (
    <MarkdownPage
      eyebrow="Coverage map"
      title={
        <>
          Kestrel vs. goAML.
          <br />
          <span className="text-landing-muted">Coverage and design decisions.</span>
        </>
      }
      subtitle="The procurement-facing answer to 'can Kestrel replace goAML for BFIU?' Every goAML feature, the Kestrel approach, and the rationale for any deviation."
      meta={[
        { label: "Document", value: "Doc 02 · Coverage" },
        { label: "Audience", value: "BFIU · Banks · Procurement" },
        { label: "Last updated", value: "2026-05-06" },
        { label: "Status", value: "Authoritative" },
      ]}
      body={body}
    />
  );
}
