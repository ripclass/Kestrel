import { AppSidebar } from "@/components/shell/app-sidebar";
import { AppTopbar } from "@/components/shell/app-topbar";
import { MobileNav } from "@/components/shell/mobile-nav";
import { isDemoModeEnabled, requireViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function PlatformLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const viewer = await requireViewer();
  const showDemoSwitcher = isDemoModeEnabled();

  return (
    <div className="platform-surface min-h-screen lg:flex">
      <AppSidebar viewer={viewer} />
      <MobileNav viewer={viewer} />
      <div className="min-w-0 flex-1">
        <AppTopbar viewer={viewer} showDemoSwitcher={showDemoSwitcher} />
        <main className="mx-auto max-w-7xl px-6 py-10 xl:px-10">{children}</main>
      </div>
    </div>
  );
}
