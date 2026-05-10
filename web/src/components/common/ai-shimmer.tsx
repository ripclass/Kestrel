/**
 * Shimmer skeleton for AI-loading states. Brutalist-styled — hairline
 * border, mono labels, monochromatic pulse — fits the Sovereign Ledger
 * platform surface. Replaces the static "Transmitting…" text states
 * the platform used previously.
 *
 * @param lines  Number of body-text lines to skeleton. Default 3.
 * @param withActions  Whether to skeleton a recommended-actions list
 *                     beneath the body. Default false.
 */
export function AiShimmer({
  lines = 3,
  withActions = false,
}: {
  lines?: number;
  withActions?: boolean;
}) {
  return (
    <div
      role="status"
      aria-label="Generating AI analysis"
      className="space-y-6"
    >
      <div className="space-y-2">
        <div className="h-2 w-24 animate-pulse bg-muted/40" />
        <div className="space-y-2">
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className="h-3 animate-pulse bg-muted/30"
              style={{ width: i === lines - 1 ? "62%" : "100%" }}
            />
          ))}
        </div>
      </div>
      {withActions ? (
        <div className="space-y-2 border-t border-border pt-6">
          <div className="h-2 w-32 animate-pulse bg-muted/40" />
          <ul className="mt-3 space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <li key={i} className="flex items-start gap-3">
                <span aria-hidden className="pt-1 font-mono leading-none text-accent">
                  ┼
                </span>
                <div
                  className="h-3 flex-1 animate-pulse bg-muted/30"
                  style={{ width: `${85 - i * 12}%` }}
                />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <span className="sr-only">Generating AI analysis…</span>
    </div>
  );
}
