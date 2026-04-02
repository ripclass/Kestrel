import Link from "next/link";

import { demoPersonaOptions } from "@/lib/demo";
import { cn } from "@/lib/utils";
import type { Persona } from "@/types/domain";

export function DemoPersonaSwitcher({
  activePersona,
}: {
  activePersona: Persona;
}) {
  return (
    <div className="hidden items-center gap-2 xl:flex">
      <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
        demo mode
      </span>
      <div className="flex items-center rounded-full border border-border/70 bg-card/90 p-1">
        {demoPersonaOptions.map((option) => (
          <Link
            key={option.persona}
            href={`/demo/${option.persona}?next=/overview`}
            className={cn(
              "rounded-full px-3 py-1.5 text-xs font-medium transition",
              option.persona === activePersona
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
            )}
          >
            {option.shortLabel}
          </Link>
        ))}
      </div>
    </div>
  );
}
