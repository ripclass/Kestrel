import { Button } from "@/components/ui/button";

const scanRuleCatalog = [
  {
    code: "rapid_cashout",
    label: "Rapid cashout",
    description:
      "High-value inbound funds exit through beneficiaries or wallets within a compressed time window.",
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
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Scan configuration
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Choose the rules to evaluate for this run. The queued scan is persisted as a real detection
          run and reuses the shared intelligence graph.
        </p>
      </div>
      <div className="space-y-5 p-6">
        <ul className="divide-y divide-border border border-border">
          {scanRuleCatalog.map((rule) => {
            const checked = selectedRules.includes(rule.code);
            return (
              <li key={rule.code}>
                <label className="flex cursor-pointer items-start gap-4 px-4 py-3 transition hover:bg-foreground/[0.03]">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-accent"
                    checked={checked}
                    onChange={() => onToggleRule(rule.code)}
                  />
                  <div className="space-y-1">
                    <p className="font-mono text-sm uppercase tracking-[0.12em] text-foreground">
                      {rule.label}
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{rule.description}</p>
                  </div>
                </label>
              </li>
            );
          })}
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            <span className="tabular-nums text-foreground">{selectedRules.length}</span> of{" "}
            <span className="tabular-nums text-foreground">{scanRuleCatalog.length}</span> rule families
            selected
          </p>
          <Button type="button" disabled={isSubmitting} onClick={onRun}>
            {isSubmitting ? "Running scan…" : "Run scan"}
          </Button>
        </div>
      </div>
    </section>
  );
}
