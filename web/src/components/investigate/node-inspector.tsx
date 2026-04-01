import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NetworkNode } from "@/types/domain";

export function NodeInspector({ node }: { node: NetworkNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Node inspector</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        <p>{node.label}</p>
        <p>{node.subtitle}</p>
        <p>Risk score {node.riskScore}</p>
      </CardContent>
    </Card>
  );
}
