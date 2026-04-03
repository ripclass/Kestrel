import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const scanRuleCatalog = [
  {
    code: "rapid_cashout",
    label: "Rapid cashout",
    description: "High-value inbound funds exit through beneficiaries or wallets within a compressed time window.",
  },
  {
    code: "fan_in_burst",
    label: "Fan-in burst",
    description: "Many inbound counterparties converge on one account over a short period.",
  },
  {
    code: "fan_out_burst",
    label: "Fan-out burst",
    description: "Funds disperse rapidly into a layered beneficiary network after landing in one account.",
  },
  {
    code: "dormant_spike",
    label: "Dormant spike",
    description: "Inactive or low-volume accounts suddenly receive unusual transaction velocity.",
  },
  {
    code: "layering",
    label: "Layering",
    description: "Movement pattern suggests deliberate path obfuscation through intermediary accounts.",
  },
  {
    code: "proximity_to_bad",
    label: "Proximity to bad",
    description: "Candidates sit near already-flagged entities in the shared intelligence graph.",
  },
  {
    code: "structuring",
    label: "Structuring",
    description: "Transactions cluster just under expected review or reporting thresholds.",
  },
  {
    code: "first_time_high_value",
    label: "First-time high value",
    description: "An account receives first-seen high-value activity inconsistent with prior behavior.",
  },
] as const;

export const defaultSelectedRules = scanRuleCatalog.map((rule) => rule.code);

export function ScanConfig({
  selectedRules,
  onToggleRule,
  onRun,
  isSubmitting,
}: {
  selectedRules: string[];
  onToggleRule: (code: string) => void;
  onRun: () => void;
  isSubmitting: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scan configuration</CardTitle>
        <CardDescription>
          Choose the rules to evaluate for this run. The queued scan is persisted as a real detection run and reuses the
          shared intelligence graph.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          {scanRuleCatalog.map((rule) => {
            const checked = selectedRules.includes(rule.code);
            return (
              <label
                key={rule.code}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/70 bg-background/40 p-3"
              >
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-input bg-background/60 accent-primary"
                  checked={checked}
                  onChange={() => onToggleRule(rule.code)}
                />
                <div className="space-y-1">
                  <p className="text-sm font-medium">{rule.label}</p>
                  <p className="text-sm text-muted-foreground">{rule.description}</p>
                </div>
              </label>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            {selectedRules.length} of {scanRuleCatalog.length} rule families selected.
          </p>
          <Button type="button" disabled={isSubmitting} onClick={onRun}>
            {isSubmitting ? "Running scan..." : "Run scan"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
