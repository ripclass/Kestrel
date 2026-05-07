import { IntakeForm } from "@/components/public/intake-form";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — Schedule a briefing",
  description:
    "Schedule a Kestrel briefing for BFIU, peer regulators, commercial banks, MFS providers, NBFIs, or accredited press.",
};

type SearchParams = { audience?: string };

const audienceCopy: Record<string, { eyebrow: string; title: string; body: string }> = {
  bfiu: {
    eyebrow: "For · BFIU and peer FIUs",
    title: "Schedule a regulator briefing.",
    body:
      "BFIU command view, cross-institutional intelligence, the goAML report lifecycle, IER workflow, and the contract framework for sovereign on-prem deployment. Briefings run as 30 to 45 minute working sessions with the founders.",
  },
  press: {
    eyebrow: "For · Press and accredited researchers",
    title: "Press and partnership intake.",
    body:
      "Founder background, architecture document, cross-bank intelligence whitepaper, and roadmap discussion. Replies within one business day.",
  },
  default: {
    eyebrow: "For · All inquiries",
    title: "Open a channel with Kestrel.",
    body:
      "Use the intake to reach the founders directly. We respond within one business day. For commercial bank pilots, the self-serve workspace at /signup/bank is faster.",
  },
};

export default async function ContactPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const key = params?.audience && audienceCopy[params.audience] ? params.audience : "default";
  const copy = audienceCopy[key];

  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 py-24 lg:grid-cols-12 lg:gap-12 lg:px-10">
          <div className="col-span-1 space-y-8 lg:col-span-5">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> {copy.eyebrow}
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              {copy.title}
            </h1>
            <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/85">
              {copy.body}
            </p>
            <div className="space-y-2 border-t border-landing-rule-solid pt-6 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-muted">
              <p>Direct · intake@kestrelfin.com</p>
              <p>Issued from · Dhaka, Bangladesh</p>
            </div>
          </div>
          <div className="col-span-1 lg:col-span-7">
            <IntakeForm />
          </div>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}
