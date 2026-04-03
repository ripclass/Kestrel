import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function UploadDrop({
  fileName,
  onFileNameChange,
}: {
  fileName: string;
  onFileNameChange: (value: string) => void;
}) {
  return (
    <Card className="grid-surface">
      <CardHeader>
        <CardTitle>Upload transactions</CardTitle>
        <CardDescription>
          Phase 7 stores scan metadata and queues a live intelligence snapshot. Raw file ingestion stays compatible with the
          later pipeline, but this cut only needs the source file label and selected rules.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-2xl border border-dashed border-primary/40 bg-background/40 px-6 py-12 text-center text-sm text-muted-foreground">
          CSV, XLSX, and statement PDF runs are represented here as named uploads. Use the file label that matches the
          batch you want in the scan history.
        </div>
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-primary">Source file label</p>
          <Input
            value={fileName}
            onChange={(event) => onFileNameChange(event.target.value)}
            placeholder="dbbl-wallet-burst-apr03.csv"
          />
        </div>
      </CardContent>
    </Card>
  );
}
