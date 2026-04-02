import { AppSidebar } from "@/components/shell/app-sidebar";
import { AppTopbar } from "@/components/shell/app-topbar";
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
    <div className="min-h-screen bg-background text-foreground lg:flex">
      <AppSidebar viewer={viewer} />
      <div className="min-w-0 flex-1">
        <AppTopbar viewer={viewer} showDemoSwitcher={showDemoSwitcher} />
        <main className="mx-auto max-w-7xl px-4 py-8 xl:px-8">{children}</main>
      </div>
    </div>
  );
}
