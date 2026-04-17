import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="bg-[#070c16]">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-6 py-12 md:grid-cols-3 lg:px-10">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-white">Kestrel</p>
          <p className="text-xs text-slate-400">
            Financial crime intelligence for Bangladesh.
          </p>
        </div>
        <nav className="flex flex-col gap-2 text-sm text-slate-300">
          <Link href="#product" className="transition hover:text-white">
            Product
          </Link>
          <Link href="#how" className="transition hover:text-white">
            How it works
          </Link>
          <a
            href="https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md"
            target="_blank"
            rel="noreferrer noopener"
            className="transition hover:text-white"
          >
            goAML coverage map
          </a>
          <Link href="/login" className="transition hover:text-white">
            Sign in
          </Link>
        </nav>
        <div className="text-right text-xs text-slate-500">
          <p>© {new Date().getFullYear()} Kestrel.</p>
          <p className="mt-1">Built in Dhaka.</p>
        </div>
      </div>
    </footer>
  );
}
