import Link from "next/link";

import { KestrelMark } from "@/components/common/kestrel-mark";

export function PublicFooter() {
  return (
    <footer className="border-t border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-16 lg:px-10">
        <div className="grid grid-cols-2 gap-y-12 gap-x-8 md:grid-cols-4">
          <div className="col-span-2 space-y-4 md:col-span-1 text-landing-foreground">
            <KestrelMark variant="lockup" size="md" />
            <p className="max-w-[220px] font-landing-body text-[11px] uppercase leading-relaxed tracking-[0.18em] text-landing-muted">
              Financial crime intelligence infrastructure. Built in Bangladesh.
            </p>
          </div>
          <div className="space-y-4">
            <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Surface
            </p>
            <ul className="space-y-2 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-foreground">
              <li>
                <Link href="#coverage" className="transition hover:text-landing-alarm">
                  Coverage
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md"
                  target="_blank"
                  rel="noreferrer noopener"
                  className="transition hover:text-landing-alarm"
                >
                  goAML map
                </a>
              </li>
              <li>
                <Link href="/login" className="transition hover:text-landing-alarm">
                  Sign in
                </Link>
              </li>
            </ul>
          </div>
          <div className="space-y-4">
            <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Protocol
            </p>
            <ul className="space-y-2 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-foreground/80">
              <li>Money Laundering Prevention Act, 2012</li>
              <li>Egmont Group intelligence exchange</li>
            </ul>
          </div>
          <div className="space-y-4">
            <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Issued
            </p>
            <p className="font-landing-body text-xs uppercase leading-relaxed tracking-[0.22em] text-landing-foreground/80">
              © {new Date().getFullYear()}
              <br />
              Dhaka, Bangladesh
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
