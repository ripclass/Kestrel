"use client";

import { Button } from "@/components/ui/button";
import { useGraphStore } from "@/stores/graph";

export function NetworkControls() {
  const { showSuspiciousOnly, toggleSuspiciousOnly } = useGraphStore();

  return (
    <Button variant="outline" size="sm" onClick={toggleSuspiciousOnly}>
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {showSuspiciousOnly ? "Show full graph" : "Show suspicious paths"}
    </Button>
  );
}
