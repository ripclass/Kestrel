import { Button } from "@/components/ui/button";

export function CaseExport() {
  return (
    <div className="flex gap-3">
      <Button>Generate PDF</Button>
      <Button variant="outline">Export evidence pack</Button>
    </div>
  );
}
