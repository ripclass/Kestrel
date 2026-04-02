import { Bell, Command } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { SearchInput } from "@/components/common/search-input";
import { DemoPersonaSwitcher } from "@/components/shell/demo-persona-switcher";
import type { Viewer } from "@/types/domain";

export function AppTopbar({
  viewer,
  showDemoSwitcher = false,
}: {
  viewer: Viewer;
  showDemoSwitcher?: boolean;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-background/90 px-4 py-4 backdrop-blur xl:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-1 items-center gap-4">
          <div className="relative max-w-2xl flex-1">
            <SearchInput placeholder="Search account, phone, wallet, NID, or business name" />
          </div>
          <Badge className="hidden bg-primary/15 text-primary lg:inline-flex">
            <Command className="mr-1.5 h-3.5 w-3.5" />
            universal search
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          {showDemoSwitcher ? (
            <DemoPersonaSwitcher activePersona={viewer.persona} />
          ) : null}
          <button className="rounded-full border border-border/70 bg-card p-2 text-muted-foreground transition hover:text-foreground">
            <Bell className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-3 rounded-full border border-border/70 bg-card px-3 py-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback>{viewer.fullName.charAt(0)}</AvatarFallback>
            </Avatar>
            <div className="hidden text-sm md:block">
              <p>{viewer.fullName}</p>
              <p className="text-xs text-muted-foreground">{viewer.persona.replaceAll("_", " ")}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
