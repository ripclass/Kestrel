import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScanConfig() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scan configuration</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Select rule families, time window, and priority channels. This scaffold keeps configuration declarative and aligned with backend YAML rule definitions.
      </CardContent>
    </Card>
  );
}
