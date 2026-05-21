import { redirect } from "next/navigation";

import { AppSidebar } from "@/components/shell/app-sidebar";
import { AppTopbar } from "@/components/shell/app-topbar";
import { MobileNav } from "@/components/shell/mobile-nav";
import { isDemoModeEnabled, isPlatformOperatorEmail, requireViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function PlatformLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const viewer = await requireViewer();

  // Platform operators are confined to the operator console — they are an
  // Enso-internal role, not a bank/BFIU tenant user. Any attempt to load a
  // tenant page (including the post-login landing on /overview) bounces to
  // the operator console, so the tenant shell + persona never render for them.
  if (isPlatformOperatorEmail(viewer.email)) {
    redirect("/platform");
  }

  const showDemoSwitcher = isDemoModeEnabled();

  return (
    <div className="platform-surface min-h-screen lg:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:border focus:border-foreground focus:bg-background focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:uppercase focus:tracking-[0.18em] focus:text-foreground"
      >
        Skip to main content
      </a>
      <AppSidebar viewer={viewer} />
      <MobileNav viewer={viewer} />
      <div className="min-w-0 flex-1">
        <AppTopbar viewer={viewer} showDemoSwitcher={showDemoSwitcher} />
        <main id="main" className="mx-auto max-w-7xl px-6 py-10 xl:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}
