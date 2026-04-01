import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportBuilder() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Report builder</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>Select briefing pack, typology digest, or compliance scorecard export.</p>
        <div className="flex gap-3">
          <Button>Generate PDF</Button>
          <Button variant="outline">Export XLSX</Button>
        </div>
      </CardContent>
    </Card>
  );
}
