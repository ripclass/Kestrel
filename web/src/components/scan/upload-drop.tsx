import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function UploadDrop() {
  return (
    <Card className="grid-surface">
      <CardHeader>
        <CardTitle>Upload transactions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-2xl border border-dashed border-primary/40 bg-background/40 px-6 py-12 text-center text-sm text-muted-foreground">
          Drop CSV, XLSX, or statement PDF files here. The first-cut scaffold keeps uploads illustrative and routes processing through detection runs.
        </div>
      </CardContent>
    </Card>
  );
}
