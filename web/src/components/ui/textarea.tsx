import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-28 w-full rounded-xl border border-input bg-background/60 px-4 py-3 text-sm outline-none placeholder:text-muted-foreground focus:border-primary",
        className,
      )}
      {...props}
    />
  );
}
