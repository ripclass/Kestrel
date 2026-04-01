import { Button } from "@/components/ui/button";

export function AlertActions() {
  return (
    <div className="flex flex-wrap gap-3">
      <Button>Escalate to case</Button>
      <Button variant="outline">Assign analyst</Button>
      <Button variant="secondary">Mark false positive</Button>
    </div>
  );
}
