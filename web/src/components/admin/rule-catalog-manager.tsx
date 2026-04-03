"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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

export function RuleCatalogManager({
  initialRules,
}: {
  initialRules: AdminRuleSummary[];
}) {
  const [rules, setRules] = useState(initialRules);
  const [drafts, setDrafts] = useState<Record<string, RuleDraft>>(
    Object.fromEntries(initialRules.map((rule) => [rule.code, toDraft(rule)])),
  );
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateDraft(code: string, patch: Partial<RuleDraft>) {
    setDrafts((current) => ({
      ...current,
      [code]: { ...current[code], ...patch },
    }));
  }

  function resetDraft(rule: AdminRuleSummary) {
    setDrafts((current) => ({
      ...current,
      [rule.code]: toDraft(rule),
    }));
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
    setRules((current) => current.map((entry) => (entry.code === updatedRule.code ? updatedRule : entry)));
    setDrafts((current) => ({
      ...current,
      [updatedRule.code]: toDraft(updatedRule),
    }));
    setNotice(`${updatedRule.name} updated.`);
    setPendingCode(null);
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="text-sm text-primary">{notice}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="grid gap-4">
        {rules.map((rule) => {
          const draft = drafts[rule.code];
          const dirty = !sameDraft(draft, toDraft(rule));

          return (
            <Card key={rule.code}>
              <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle>{rule.name}</CardTitle>
                    <Badge>{rule.code}</Badge>
                    <Badge className={rule.isSystem ? "" : "border-primary/30 bg-primary/15 text-primary"}>
                      {rule.source}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{rule.category}</p>
                </div>
                <Badge
                  className={
                    draft.isActive
                      ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-100"
                      : "border-slate-400/30 bg-slate-500/15 text-slate-200"
                  }
                >
                  {draft.isActive ? `live v${rule.version}` : `inactive v${rule.version}`}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">{rule.description}</p>
                <div className="grid gap-4 md:grid-cols-[0.7fr_0.7fr_1fr_auto]">
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Weight</span>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={draft.weight}
                      onChange={(event) => updateDraft(rule.code, { weight: event.target.value })}
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Threshold</span>
                    <Input
                      type="number"
                      step="1"
                      min="0"
                      value={draft.threshold}
                      onChange={(event) => updateDraft(rule.code, { threshold: event.target.value })}
                      placeholder="Inherited"
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Description override</span>
                    <Input
                      value={draft.description}
                      onChange={(event) => updateDraft(rule.code, { description: event.target.value })}
                    />
                  </label>
                  <label className="flex items-end gap-2 pb-3 text-sm">
                    <input
                      type="checkbox"
                      checked={draft.isActive}
                      onChange={(event) => updateDraft(rule.code, { isActive: event.target.checked })}
                    />
                    <span className="text-muted-foreground">Active</span>
                  </label>
                </div>
                <div className="flex gap-3">
                  <Button
                    type="button"
                    disabled={!dirty || pendingCode === rule.code}
                    onClick={() => void saveRule(rule)}
                  >
                    {pendingCode === rule.code ? "Saving..." : "Save rule"}
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
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
