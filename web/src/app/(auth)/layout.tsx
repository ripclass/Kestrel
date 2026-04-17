import { KestrelMark } from "@/components/common/kestrel-mark";

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <main className="platform-surface relative min-h-screen">
      <div className="pointer-events-none absolute inset-0 platform-grid-overlay [mask-image:linear-gradient(to_bottom,transparent,black,transparent)]" />
      <header className="relative z-10 border-b border-border">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <KestrelMark variant="lockup" size="md" />
          <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
            Cleared-access intake
          </p>
        </div>
      </header>
      <section className="relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center px-6 py-16 lg:px-10">
        <div className="w-full max-w-lg">{children}</div>
      </section>
    </main>
  );
}
