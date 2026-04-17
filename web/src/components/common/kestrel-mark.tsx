import { cn } from "@/lib/utils";

/**
 * Kestrel brand mark — single source of truth.
 *
 * When the real SVG logo arrives, swap the `┼` glyph span in the
 * lockup / mark variants for an <svg> or <Image> import. Every surface
 * (landing header/footer, sidebar, topbar, auth pages, PDF exports, email
 * templates) renders the new logo on next build — no hunting.
 *
 * Variants:
 *   - "lockup"   : mark + wordmark (default — headers, footers, splash).
 *   - "mark"     : mark only (favicon slot, compact rails).
 *   - "wordmark" : text only (inline mentions, legal footers).
 */
export function KestrelMark({
  variant = "lockup",
  size = "md",
  className,
}: {
  variant?: "lockup" | "mark" | "wordmark";
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizes = {
    sm: { glyph: "text-sm", text: "text-xs" },
    md: { glyph: "text-base", text: "text-sm" },
    lg: { glyph: "text-2xl", text: "text-xl" },
  }[size];

  if (variant === "mark") {
    return (
      <span
        role="img"
        aria-label="Kestrel"
        className={cn("inline-flex items-center leading-none text-accent", sizes.glyph, className)}
      >
        ┼
      </span>
    );
  }

  if (variant === "wordmark") {
    return (
      <span
        className={cn(
          "font-mono uppercase tracking-[0.22em]",
          sizes.text,
          className,
        )}
      >
        Kestrel
      </span>
    );
  }

  return (
    <span className={cn("inline-flex items-baseline gap-2", className)}>
      <span aria-hidden className={cn("leading-none text-accent", sizes.glyph)}>
        ┼
      </span>
      <span className={cn("font-mono uppercase tracking-[0.22em]", sizes.text)}>
        Kestrel
      </span>
    </span>
  );
}
