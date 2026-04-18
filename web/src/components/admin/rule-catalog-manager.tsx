"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AdminRuleMutationResponse } from "@/types/api";
import type { AdminRuleSummary } from "@/types/domain";

type RuleDraft = {
  isActive: boolean;
  weight: string;
  threshold: string;
  description: string;
};

function toDraft(rule: AdminRuleSummary): RuleDraft {
  return {
    isActive: rule.isActive,
    weight: rule.weight.toFixed(2),
    threshold: rule.threshold?.toString() ?? "",
    description: rule.description,
  };
}

function sameDraft(left: RuleDraft, right: RuleDraft) {
  return (
    left.isActive === right.isActive &&
    left.weight === right.weight &&
    left.threshold === right.threshold &&
    left.description === right.description
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

export function RuleCatalogManager({ initialRules }: { initialRules: AdminRuleSummary[] }) {
  const [rules, setRules] = useState(initialRules);
  const [drafts, setDrafts] = useState<Record<string, RuleDraft>>(
    Object.fromEntries(initialRules.map((rule) => [rule.code, toDraft(rule)])),
  );
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateDraft(code: string, patch: Partial<RuleDraft>) {
    setDrafts((current) => ({ ...current, [code]: { ...current[code], ...patch } }));
  }

  function resetDraft(rule: AdminRuleSummary) {
    setDrafts((current) => ({ ...current, [rule.code]: toDraft(rule) }));
  }

  async function saveRule(rule: AdminRuleSummary) {
    const draft = drafts[rule.code];
    setPendingCode(rule.code);
    setNotice(null);
    setError(null);

    const response = await fetch(`/api/admin/rules/${encodeURIComponent(rule.code)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        isActive: draft.isActive,
        weight: Number.parseFloat(draft.weight),
        threshold: draft.threshold.trim() === "" ? null : Number.parseFloat(draft.threshold),
        description: draft.description.trim() === "" ? null : draft.description.trim(),
      }),
    });
    const payload = await readResponsePayload<AdminRuleMutationResponse>(response);

    if (!response.ok) {
      setError(detailFromPayload(payload, "Unable to update rule configuration."));
      setPendingCode(null);
      return;
    }

    const updatedRule = (payload as AdminRuleMutationResponse).rule;
    setRules((current) =>
      current.map((entry) => (entry.code === updatedRule.code ? updatedRule : entry)),
    );
    setDrafts((current) => ({ ...current, [updatedRule.code]: toDraft(updatedRule) }));
    setNotice(`${updatedRule.name} updated.`);
    setPendingCode(null);
  }

  return (
    <div className="space-y-4">
      {notice ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
          <span aria-hidden className="mr-2">┼</span>
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          <span aria-hidden className="mr-2">┼</span>ERROR · {error}
        </p>
      ) : null}
      <div className="grid gap-4">
        {rules.map((rule) => {
          const draft = drafts[rule.code];
          const dirty = !sameDraft(draft, toDraft(rule));

          return (
            <section key={rule.code} className="border border-border">
              <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                      <span aria-hidden className="mr-2 text-accent">┼</span>
                      Rule · {rule.code}
                    </p>
                  </div>
                  <h3 className="text-base font-semibold text-foreground">{rule.name}</h3>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {rule.category}
                    </span>
                    <span
                      className={`border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${
                        rule.isSystem
                          ? "border-border text-muted-foreground"
                          : "border-accent/40 text-accent"
                      }`}
                    >
                      {rule.source}
                    </span>
                  </div>
                </div>
                <span
                  className={`border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] ${
                    draft.isActive
                      ? "border-accent/40 bg-accent/10 text-accent"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  {draft.isActive ? `live · v${rule.version}` : `inactive · v${rule.version}`}
                </span>
              </div>
              <div className="space-y-5 p-6">
                <p className="text-sm leading-relaxed text-muted-foreground">{rule.description}</p>
                <div className="grid gap-4 md:grid-cols-[0.7fr_0.7fr_1fr_auto]">
                  <Field label="Weight">
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={draft.weight}
                      onChange={(event) => updateDraft(rule.code, { weight: event.target.value })}
                    />
                  </Field>
                  <Field label="Threshold">
                    <Input
                      type="number"
                      step="1"
                      min="0"
                      value={draft.threshold}
                      onChange={(event) => updateDraft(rule.code, { threshold: event.target.value })}
                      placeholder="Inherited"
                    />
                  </Field>
                  <Field label="Description override">
                    <Input
                      value={draft.description}
                      onChange={(event) => updateDraft(rule.code, { description: event.target.value })}
                    />
                  </Field>
                  <label className="flex items-end gap-2 pb-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={draft.isActive}
                      onChange={(event) =>
                        updateDraft(rule.code, { isActive: event.target.checked })
                      }
                    />
                    <span>Active</span>
                  </label>
                </div>
                <div className="flex gap-2 border-t border-border pt-4">
                  <Button
                    type="button"
                    disabled={!dirty || pendingCode === rule.code}
                    onClick={() => void saveRule(rule)}
                  >
                    {pendingCode === rule.code ? "Saving…" : "Save rule"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!dirty || pendingCode === rule.code}
                    onClick={() => resetDraft(rule)}
                  >
                    Reset
                  </Button>
                </div>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
