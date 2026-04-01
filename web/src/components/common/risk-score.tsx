import { Badge } from "@/components/ui/badge";
import { severityColorMap } from "@/lib/constants";
import type { Severity } from "@/types/domain";

export function RiskScore({ score, severity }: { score: number; severity: Severity }) {
  return (
    <Badge className={severityColorMap[severity]}>
      {score}
      <span className="ml-1 opacity-75">/100</span>
    </Badge>
  );
}
