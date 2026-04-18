import Link from "next/link";

import { KestrelMark } from "@/components/common/kestrel-mark";

const navLinks = [
  { href: "#coverage", label: "Coverage" },
  {
    href: "https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md",
    label: "goAML Map",
    external: true,
  },
  { href: "/login", label: "Sign in" },
];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-landing-rule bg-landing-bg/90 backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-10">
        <Link href="/" className="flex items-center gap-3 text-landing-foreground">
          <KestrelMark variant="lockup" size="md" />
          <span className="hidden font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted sm:inline">
            BGD · Financial Intelligence
          </span>
        </Link>
        <nav className="hidden items-center gap-8 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-muted md:flex">
          {navLinks.map((link) =>
            link.external ? (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noreferrer noopener"
                className="transition hover:text-landing-foreground"
              >
                {link.label}
              </a>
            ) : (
              <Link key={link.href} href={link.href} className="transition hover:text-landing-foreground">
                {link.label}
              </Link>
            ),
          )}
        </nav>
        <Link
          href="#access"
          className="inline-flex items-center gap-2 border border-landing-alarm px-4 py-2 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-alarm transition hover:bg-landing-alarm hover:text-landing-bg"
        >
          Request clearance
        </Link>
      </div>
    </header>
  );
}
