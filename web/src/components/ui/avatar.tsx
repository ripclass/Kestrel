/* eslint-disable @next/next/no-img-element */
import type { HTMLAttributes, ImgHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Avatar({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("relative flex h-10 w-10 overflow-hidden rounded-full border border-border", className)}
      {...props}
    />
  );
}

export function AvatarImage({ className, ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  return <img alt={props.alt ?? ""} className={cn("h-full w-full object-cover", className)} {...props} />;
}

export function AvatarFallback({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center bg-primary/20 text-sm font-semibold text-primary",
        className,
      )}
      {...props}
    />
  );
}
