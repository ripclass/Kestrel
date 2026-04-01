import { detectionRuns } from "@/lib/demo";
import { FlaggedAccountCard } from "@/components/scan/flagged-account-card";

export function ScanResults() {
  const latest = detectionRuns[0];

  return (
    <div className="space-y-3">
      <FlaggedAccountCard label={`${latest.fileName} / likely mule account`} score={94} />
      <FlaggedAccountCard label="Secondary beneficiary cluster" score={82} />
    </div>
  );
}
