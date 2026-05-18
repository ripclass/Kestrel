import { SidebarNav } from "@/components/shell/sidebar-nav";
import type { Viewer } from "@/types/domain";

export function AppSidebar({ viewer }: { viewer: Viewer }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] lg:flex">
      <SidebarNav viewer={viewer} />
    </aside>
  );
}
