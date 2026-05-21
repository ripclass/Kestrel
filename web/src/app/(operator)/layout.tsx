import { OperatorSidebar } from "@/components/operator/operator-sidebar";
import { OperatorTopbar } from "@/components/operator/operator-topbar";
import { platformOperatorRole, requirePlatformOperator } from "@/lib/auth";

export const dynamic = "force-dynamic";

/**
 * Operator-console shell — Enso-internal, gated by the operator allow-list.
 * Deliberately separate from the (platform) tenant shell: an operator is not
 * a bank/BFIU user and sees no tenant tools, only operator modules.
 */
export default async function OperatorLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const viewer = await requirePlatformOperator();
  const role = platformOperatorRole(viewer.email) ?? "owner";
  const identity = {
    name: viewer.fullName || "Operator",
    email: viewer.email,
    role,
  };

  return (
    <div className="platform-surface min-h-screen lg:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:border focus:border-foreground focus:bg-background focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:uppercase focus:tracking-[0.18em] focus:text-foreground"
      >
        Skip to main content
      </a>
      <OperatorSidebar identity={identity} />
      <div className="min-w-0 flex-1">
        <OperatorTopbar email={viewer.email} />
        <main id="main" className="mx-auto max-w-7xl px-6 py-10 xl:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}
