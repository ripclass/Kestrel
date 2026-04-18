import { cn } from "@/lib/utils";

/**
 * Kestrel brand mark — single source of truth.
 *
 * The bird silhouette uses `fill="currentColor"` so it inherits whatever
 * text colour the parent scopes (bone on dark surfaces, slate on light
 * exports). The embedded crosshair is hard-pinned to the vermillion
 * accent via `var(--accent, #ff3823)` — the fallback guarantees it still
 * renders in vermillion on the landing even though the landing doesn't
 * expose the `--accent` token.
 *
 * Variants:
 *   - "lockup"   : mark + wordmark (default — headers, footers, splash).
 *   - "mark"     : mark only (favicon slot, compact rails).
 *   - "wordmark" : text only (inline mentions, legal footers).
 */

const sizeMap = {
  sm: { mark: "h-4", wordmark: "h-2.5", gap: "gap-2" },
  md: { mark: "h-6", wordmark: "h-3", gap: "gap-3" },
  lg: { mark: "h-10", wordmark: "h-5", gap: "gap-4" },
};

function MarkSvg({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 254.04 166.3"
      aria-hidden
      className={cn("block w-auto shrink-0", className)}
    >
      <path
        fill="currentColor"
        d="M0,0S77.33,47.6,97.22,62.91s7.67,26.19,7.67,26.19c0,0-39.19,35.87-98.85,77.21,45.5-10.26,79.47-20.72,158.24-46.26,.98-.32,1.96-.67,2.92-1.04,9.16-3.51,41.08-14.87,44.81-39.09,1.57-10.21,10.17-17.97,20.5-17.74,10.93,.24,21.52,4.5,21.52,4.5l-16.25-25.94s-14.14-22.43-61.47-18.6c-6.61,.53-13.25,.61-19.86,.1C93.28,17.38,0,0,0,0Z"
      />
      <path
        fill="var(--accent, #ff3823)"
        d="M203.51,46.43h-8.06v-2.19h8.06V27.73h2.19v16.51h8.06v2.19h-8.06v15.87h-2.19v-15.87Z"
      />
    </svg>
  );
}

function WordmarkSvg({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 248.85 44.18"
      aria-hidden
      className={cn("block w-auto shrink-0", className)}
    >
      <path
        fill="currentColor"
        d="M12.48,24.72l-4.47,5.87v12.85H0V.73H8.02V19.95h.37l4.96-7.1L22.33,.73h9.06l-13.4,17.99,14.01,24.72h-9.06L12.48,24.72Z"
      />
      <path
        fill="currentColor"
        d="M37.32,43.44V.73h26.98V7.34h-18.97v11.14h18.29v6.61h-18.29v11.75h18.97v6.61h-26.98Z"
      />
      <path
        fill="currentColor"
        d="M86.82,44.18c-3.67,0-6.8-.63-9.39-1.88-2.59-1.25-4.7-2.91-6.33-4.97l4.83-5.02c1.59,1.83,3.31,3.19,5.17,4.07,1.86,.88,3.84,1.32,5.97,1.32,2.45,0,4.32-.55,5.63-1.66,1.31-1.11,1.96-2.71,1.96-4.81,0-1.73-.49-3.03-1.47-3.92-.98-.88-2.63-1.51-4.96-1.88l-4.53-.73c-3.96-.69-6.77-2.13-8.44-4.31-1.67-2.18-2.51-4.76-2.51-7.73,0-4.07,1.33-7.2,3.98-9.38,2.65-2.18,6.32-3.27,11.01-3.27,3.34,0,6.23,.53,8.66,1.58,2.43,1.05,4.38,2.48,5.84,4.3l-4.71,5.01c-1.14-1.35-2.51-2.42-4.1-3.21s-3.47-1.19-5.63-1.19c-4.65,0-6.98,1.93-6.98,5.8,0,1.64,.49,2.9,1.47,3.76s2.65,1.5,5.02,1.91l4.47,.79c3.71,.69,6.46,2.06,8.26,4.1,1.79,2.04,2.69,4.64,2.69,7.82,0,2-.35,3.82-1.04,5.47-.69,1.65-1.71,3.08-3.06,4.28-1.35,1.2-3.01,2.13-4.99,2.78-1.98,.65-4.25,.98-6.82,.98Z"
      />
      <path
        fill="currentColor"
        d="M128,7.34V43.44h-7.96V7.34h-12.85V.73h33.65V7.34h-12.85Z"
      />
      <path
        fill="currentColor"
        d="M155.29,43.44h-8.01V.73h16.21c4.16,0,7.34,1.18,9.55,3.55,2.2,2.37,3.3,5.59,3.3,9.67,0,3.14-.72,5.78-2.17,7.92-1.45,2.14-3.52,3.5-6.21,4.07l9.12,17.5h-8.81l-8.14-16.58h-4.83v16.58Zm6.55-22.82c2.16,0,3.71-.44,4.65-1.32,.94-.88,1.41-2.29,1.41-4.21v-2.34c0-1.93-.47-3.33-1.41-4.21-.94-.88-2.49-1.32-4.65-1.32h-6.55v13.4h6.55Z"
      />
      <path
        fill="currentColor"
        d="M184.17,43.44V.73h26.98V7.34h-18.97v11.14h18.3v6.61h-18.3v11.75h18.97v6.61h-26.98Z"
      />
      <path
        fill="currentColor"
        d="M221.93,43.44V.73h8.02V36.83h18.91v6.61h-26.92Z"
      />
    </svg>
  );
}

export function KestrelMark({
  variant = "lockup",
  size = "md",
  className,
}: {
  variant?: "lockup" | "mark" | "wordmark";
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const cfg = sizeMap[size];

  if (variant === "mark") {
    return (
      <span
        role="img"
        aria-label="Kestrel"
        className={cn("inline-flex items-center", className)}
      >
        <MarkSvg className={cfg.mark} />
      </span>
    );
  }

  if (variant === "wordmark") {
    return (
      <span
        role="img"
        aria-label="Kestrel"
        className={cn("inline-flex items-center", className)}
      >
        <WordmarkSvg className={cfg.wordmark} />
      </span>
    );
  }

  return (
    <span
      role="img"
      aria-label="Kestrel"
      className={cn("inline-flex items-center", cfg.gap, className)}
    >
      <MarkSvg className={cfg.mark} />
      <WordmarkSvg className={cfg.wordmark} />
    </span>
  );
}
