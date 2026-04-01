import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none ring-0 placeholder:text-muted-foreground focus:border-primary",
        className,
      )}
      {...props}
    />
  );
}
