"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type {
  DisseminationListResponse,
} from "@/types/api";
import type { DisseminationSummary, RecipientType, Viewer } from "@/types/domain";

const RECIPIENT_TYPES: RecipientType[] = [
  "law_enforcement",
  "regulator",
  "foreign_fiu",
  "prosecutor",
  "other",
];

const recipientTypeLabel: Record<RecipientType, string> = {
  law_enforcement: "Law enforcement",
  regulator: "Regulator",
  foreign_fiu: "Foreign FIU",
  prosecutor: "Prosecutor",
  other: "Other",
};

const recipientTypeBadge: Record<RecipientType, string> = {
  law_enforcement: "bg-red-500/20 text-red-300 border-red-500/30",
  regulator: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  foreign_fiu: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  prosecutor: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  other: "bg-slate-500/20 text-slate-300 border-slate-500/30",
};

type RecipientFilter = "all" | RecipientType;

export function DisseminationList({ viewer }: { viewer: Viewer }) {
  const [records, setRecords] = useState<DisseminationSummary[]>([]);
  const [filter, setFilter] = useState<RecipientFilter>("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const url = filter === "all" ? "/api/disseminations" : `/api/disseminations?recipient_type=${filter}`;
      const response = await fetch(url, { cache: "no-store" });
      const payload = (await readResponsePayload<DisseminationListResponse>(response)) as
        | DisseminationListResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load disseminations."));
        return;
      }
      setRecords((payload as DisseminationListResponse).disseminations);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load disseminations.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  const canDisseminate = useMemo(() => viewer.role !== "viewer", [viewer.role]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Record a new dissemination</CardTitle>
              <CardDescription>
                Capture the recipient, classification, subject summary, and linked reports in one step. Every dissemination is logged to the audit trail.
              </CardDescription>
            </div>
            {canDisseminate ? (
              <DisseminateAction onCompleted={() => void loadRecords()} triggerLabel="New dissemination" variant="default" />
            ) : null}
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dissemination ledger</CardTitle>
          <CardDescription>Filter by recipient type to audit specific agencies or review all outbound intelligence.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {(["all", ...RECIPIENT_TYPES] as RecipientFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  filter === type
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {type === "all" ? "All" : recipientTypeLabel[type]}
              </button>
            ))}
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading disseminations…</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No disseminations recorded yet. Open a case or alert and use the &ldquo;Disseminate&rdquo; action, or start a new record above.
            </p>
          ) : (
            records.map((record) => (
              <Link
                key={record.id}
                href={`/intelligence/disseminations/${record.id}`}
                className="block rounded-2xl border border-border/80 bg-background/50 p-4 transition hover:border-primary/60 hover:bg-background/70"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{record.disseminationRef}</h3>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-widest ${recipientTypeBadge[record.recipientType]}`}
                      >
                        {recipientTypeLabel[record.recipientType]}
                      </span>
                      <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        {record.classification}
                      </span>
                    </div>
                    <p className="text-sm">{record.recipientAgency}</p>
                    <p className="text-sm text-muted-foreground">{record.subjectSummary}</p>
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p>Reports linked: {record.linkedReportCount}</p>
                    <p>Entities linked: {record.linkedEntityCount}</p>
                    <p>Cases linked: {record.linkedCaseCount}</p>
                    <p>Disseminated: {new Date(record.disseminatedAt).toLocaleString()}</p>
                  </div>
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
