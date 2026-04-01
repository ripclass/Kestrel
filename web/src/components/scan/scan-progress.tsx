import { detectionRuns } from "@/lib/demo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScanProgress() {
  const activeRun = detectionRuns.find((run) => run.status === "processing") ?? detectionRuns[0];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active run</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        <p>{activeRun.fileName}</p>
        <p>{activeRun.accountsScanned.toLocaleString()} accounts scanned</p>
      </CardContent>
    </Card>
  );
}
