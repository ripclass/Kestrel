"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DisseminationListResponse } from "@/types/api";
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

const recipientTypeTone: Record<RecipientType, string> = {
  law_enforcement: "border-accent/40 text-accent",
  regulator: "border-foreground/30 text-foreground",
  foreign_fiu: "border-foreground/30 text-foreground",
  prosecutor: "border-accent/40 text-accent",
  other: "border-border text-muted-foreground",
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
      const url =
        filter === "all" ? "/api/disseminations" : `/api/disseminations?recipient_type=${filter}`;
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
      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · Record a new dissemination
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Capture the recipient, classification, subject summary, and linked reports in one step.
              Every dissemination is logged to the audit trail.
            </p>
          </div>
          {canDisseminate ? (
            <DisseminateAction
              onCompleted={() => void loadRecords()}
              triggerLabel="New dissemination"
              variant="default"
            />
          ) : null}
        </div>
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Dissemination ledger
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Filter by recipient type to audit specific agencies or review all outbound intelligence.
          </p>
        </div>
        <div className="space-y-4 p-6">
          <div className="flex flex-wrap gap-0 border border-border">
            {(["all", ...RECIPIENT_TYPES] as RecipientFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`border-r border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                  filter === type
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
                }`}
              >
                {type === "all" ? "All" : recipientTypeLabel[type]}
              </button>
            ))}
          </div>
          {error ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              <span aria-hidden className="mr-2">┼</span>ERROR · {error}
            </p>
          ) : null}
          {loading ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Loading disseminations…
            </p>
          ) : records.length === 0 ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              No disseminations recorded yet. Open a case or alert and use the &ldquo;Disseminate&rdquo;
              action, or start a new record above.
            </p>
          ) : (
            <div className="space-y-3">
              {records.map((record) => (
                <Link
                  key={record.id}
                  href={`/intelligence/disseminations/${record.id}`}
                  className="block border border-border bg-card px-5 py-4 transition hover:bg-foreground/[0.03]"
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-mono text-base text-foreground">{record.disseminationRef}</h3>
                        <span
                          className={`inline-flex items-center border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${recipientTypeTone[record.recipientType]}`}
                        >
                          {recipientTypeLabel[record.recipientType]}
                        </span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                          {record.classification}
                        </span>
                      </div>
                      <p className="text-sm text-foreground">{record.recipientAgency}</p>
                      <p className="text-sm leading-relaxed text-muted-foreground">
                        {record.subjectSummary}
                      </p>
                    </div>
                    <div className="space-y-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      <p>
                        Reports linked ·{" "}
                        <span className="tabular-nums text-foreground">{record.linkedReportCount}</span>
                      </p>
                      <p>
                        Entities linked ·{" "}
                        <span className="tabular-nums text-foreground">{record.linkedEntityCount}</span>
                      </p>
                      <p>
                        Cases linked ·{" "}
                        <span className="tabular-nums text-foreground">{record.linkedCaseCount}</span>
                      </p>
                      <p>
                        Disseminated ·{" "}
                        <span className="text-foreground">
                          {new Date(record.disseminatedAt).toLocaleString()}
                        </span>
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
