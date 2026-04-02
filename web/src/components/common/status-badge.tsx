import { Badge } from "@/components/ui/badge";

const statusClassMap: Record<string, string> = {
  open: "border-sky-400/30 bg-sky-500/15 text-sky-300",
  draft: "border-zinc-400/30 bg-zinc-500/15 text-zinc-200",
  submitted: "border-sky-400/30 bg-sky-500/15 text-sky-300",
  under_review: "border-amber-400/30 bg-amber-500/15 text-amber-300",
  flagged: "border-red-400/30 bg-red-500/15 text-red-300",
  confirmed: "border-red-400/30 bg-red-500/15 text-red-300",
  dismissed: "border-emerald-400/30 bg-emerald-500/15 text-emerald-300",
  reviewing: "border-amber-400/30 bg-amber-500/15 text-amber-300",
  escalated: "border-red-400/30 bg-red-500/15 text-red-300",
  true_positive: "border-red-400/30 bg-red-500/15 text-red-300",
  false_positive: "border-emerald-400/30 bg-emerald-500/15 text-emerald-300",
  investigating: "border-amber-400/30 bg-amber-500/15 text-amber-300",
  completed: "border-emerald-400/30 bg-emerald-500/15 text-emerald-300",
  processing: "border-sky-400/30 bg-sky-500/15 text-sky-300",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge className={statusClassMap[status] ?? "bg-white/5"}>{status.replaceAll("_", " ")}</Badge>;
}
