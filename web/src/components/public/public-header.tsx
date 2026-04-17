import Link from "next/link";

import { Button } from "@/components/ui/button";

const navLinks = [
  { href: "#product", label: "Product" },
  { href: "#how", label: "How it works" },
  {
    href: "https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md",
    label: "Coverage",
    external: true,
  },
];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-[#09111d]/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-10">
        <Link href="/" className="flex items-baseline gap-3">
          <span className="text-lg font-semibold tracking-tight text-white">Kestrel</span>
          <span className="hidden text-xs uppercase tracking-[0.28em] text-primary sm:inline">
            Financial Crime Intelligence
          </span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
          {navLinks.map((link) =>
            link.external ? (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noreferrer noopener"
                className="transition hover:text-white"
              >
                {link.label}
              </a>
            ) : (
              <Link key={link.href} href={link.href} className="transition hover:text-white">
                {link.label}
              </Link>
            ),
          )}
          <Link href="/login" className="transition hover:text-white">
            Sign in
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/login" className="hidden text-sm text-slate-300 transition hover:text-white md:inline">
            Sign in
          </Link>
          <Link href="#access">
            <Button size="sm">Request access</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
