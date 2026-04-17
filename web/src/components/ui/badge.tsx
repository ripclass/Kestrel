import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-border bg-white/5 px-2.5 py-1 text-xs font-medium",
        className,
      )}
      {...props}
    />
  );
}
