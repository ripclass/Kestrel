"use client";

import { Button } from "@/components/ui/button";
import { useGraphStore } from "@/stores/graph";

export function NetworkControls() {
  const { showSuspiciousOnly, toggleSuspiciousOnly } = useGraphStore();

  return (
    <div className="flex gap-3">
      <Button variant="outline" onClick={toggleSuspiciousOnly}>
        {showSuspiciousOnly ? "Show full graph" : "Show suspicious paths"}
      </Button>
    </div>
  );
}
