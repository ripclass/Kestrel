import type { ReactNode } from "react";
import Link from "next/link";

export function DocSection({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-5xl px-6 py-16 lg:px-10 lg:py-20">
        <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
          <span className="leading-none">┼</span> {eyebrow}
        </span>
        <h2 className="mt-4 font-landing-display text-2xl leading-tight text-landing-foreground lg:text-4xl">
          {title}
        </h2>
        {children}
      </div>
    </section>
  );
}

export function DocCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-landing-bg p-5">
      <dt className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
        {label}
      </dt>
      <dd className="mt-2 font-landing-mono text-sm uppercase tracking-[0.06em] text-landing-foreground">
        {value}
      </dd>
    </div>
  );
}

export function DocCode({ children }: { children: string }) {
  return (
    <pre className="mt-6 overflow-x-auto border border-landing-rule-solid bg-[color:var(--landing-bg-elevated,#15171c)] p-4 font-landing-mono text-[12px] leading-relaxed text-landing-foreground/85">
      <code>{children}</code>
    </pre>
  );
}

export function DocMono({ children }: { children: ReactNode }) {
  return (
    <code className="border border-landing-rule-solid bg-[color:var(--landing-bg-elevated,#15171c)] px-1.5 py-0.5 font-landing-mono text-[12px] uppercase tracking-[0.06em] text-landing-foreground/90">
      {children}
    </code>
  );
}

export function DocTable({ children }: { children: ReactNode }) {
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full border-collapse border border-landing-rule-solid font-landing-body text-[13px] text-landing-foreground/85">
        {children}
      </table>
    </div>
  );
}

export function DocTh({ children }: { children: ReactNode }) {
  return (
    <th className="border-b border-r border-landing-rule-solid bg-[color:var(--landing-bg-elevated,#15171c)] p-3 text-left font-landing-body text-[10px] uppercase tracking-[0.22em] text-landing-muted last:border-r-0">
      {children}
    </th>
  );
}

export function DocTd({ children }: { children: ReactNode }) {
  return (
    <td className="border-b border-r border-landing-rule-solid p-3 align-top last:border-r-0">
      {children}
    </td>
  );
}

export function DocFinalCta({ heading }: { heading: string }) {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-5xl px-6 py-20 lg:px-10 lg:py-24">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-4">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Next step
            </span>
            <h2 className="font-landing-display text-2xl leading-tight text-landing-foreground lg:text-4xl">
              {heading}
            </h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/signup/bank"
              className="inline-flex items-center gap-3 border border-landing-alarm px-6 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-alarm transition hover:bg-landing-alarm hover:text-landing-bg"
            >
              Run a pilot →
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-3 border border-landing-rule-solid px-6 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground/85 transition hover:border-landing-foreground hover:text-landing-foreground"
            >
              Schedule a briefing →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
