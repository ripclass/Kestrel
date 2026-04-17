import { Badge } from "@/components/ui/badge";

/**
 * Status semantics collapsed to Sovereign Ledger's three-tone system:
 *   - ALARM    — vermillion accent. Active, flagged, confirmed, escalated, failed.
 *   - ACTIVE   — bone foreground, solid. Mid-flight work.
 *   - MUTED    — dimmed. Resolved, dismissed, drafted, completed, pending.
 *
 * In the legacy dark theme (non-platform scope) these map to the existing
 * accent / foreground / muted tokens — colour shifts palette but semantics
 * hold.
 */
const alarm = "border-accent/40 bg-accent/10 text-accent";
const active = "border-foreground/30 bg-foreground/10 text-foreground";
const muted = "border-border bg-white/[0.03] text-muted-foreground";

const statusClassMap: Record<string, string> = {
  open: active,
  draft: muted,
  submitted: active,
  under_review: active,
  flagged: alarm,
  confirmed: alarm,
  dismissed: muted,
  reviewing: active,
  escalated: alarm,
  true_positive: alarm,
  false_positive: muted,
  investigating: active,
  completed: muted,
  processing: active,
  pending: muted,
  failed: alarm,
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge className={`${statusClassMap[status] ?? muted} font-mono uppercase tracking-[0.12em]`}>
      {status.replaceAll("_", " ")}
    </Badge>
  );
}
