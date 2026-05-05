import Link from "next/link";

import { StatusBoard } from "@/components/status/status-board";

export const dynamic = "force-dynamic";
export const revalidate = 30;

export default function PublicStatusPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10 flex items-baseline justify-between border-b border-landing-foreground/10 pb-6">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
            <span aria-hidden className="mr-2 text-landing-accent">┼</span>
            Kestrel · Status
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-landing-foreground">
            Platform health
          </h1>
        </div>
        <Link
          href="/"
          className="font-mono text-[11px] uppercase tracking-[0.22em] text-landing-foreground/60 transition hover:text-landing-foreground"
        >
          ← back to kestrel
        </Link>
      </header>
      <StatusBoard />
      <footer className="mt-16 space-y-2 border-t border-landing-foreground/10 pt-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/60">
          ┼ SLA · 99.5% Professional · 99.9% Enterprise
        </p>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/60">
          Status updates every 5 minutes from kestrel-engine.onrender.com
        </p>
      </footer>
    </div>
  );
}
