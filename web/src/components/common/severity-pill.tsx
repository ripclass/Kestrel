import { Badge } from "@/components/ui/badge";
import { severityColorMap } from "@/lib/constants";
import type { Severity } from "@/types/domain";

export function SeverityPill({ severity }: { severity: Severity }) {
  return <Badge className={severityColorMap[severity]}>{severity}</Badge>;
}
