"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DisseminationDetail } from "@/types/domain";

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}

function Section({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {label}
        </p>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

export function DisseminationWorkspace({ disseminationId }: { disseminationId: string }) {
  const [record, setRecord] = useState<DisseminationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/disseminations/${disseminationId}`, { cache: "no-store" });
        const payload = (await readResponsePayload<DisseminationDetail>(response)) as
          | DisseminationDetail
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load dissemination."));
          return;
        }
        setRecord(payload as DisseminationDetail);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load dissemination.");
      }
    })();
  }, [disseminationId]);

  if (error) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>ERROR · {error}
      </p>
    );
  }
  if (!record) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        <span aria-hidden className="mr-2 text-accent">┼</span>Loading dissemination…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="leading-none text-accent">┼</span>
              Dissemination · {record.disseminationRef}
            </p>
            <h2 className="font-mono text-2xl text-foreground">{record.disseminationRef}</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {record.recipientAgency} ·{" "}
              <span className="font-mono uppercase">{record.classification}</span>
            </p>
          </div>
          <Link
            href="/intelligence/disseminations"
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
          >
            ← Back to disseminations
          </Link>
        </div>
        <div className="grid grid-cols-2 divide-x divide-y divide-border lg:grid-cols-4 lg:divide-y-0">
          <Meta label="Recipient">
            <span className="text-sm text-foreground">{record.recipientAgency}</span>
          </Meta>
          <Meta label="Recipient type">
            <span className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">
              {record.recipientType.replace("_", " ")}
            </span>
          </Meta>
          <Meta label="Classification">
            <span className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">
              {record.classification}
            </span>
          </Meta>
          <Meta label="Disseminated">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground">
              {new Date(record.disseminatedAt).toLocaleString()}
            </span>
          </Meta>
        </div>
      </section>

      <Section
        label="Subject summary"
        description="The narrative sent alongside the underlying reports and entities."
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {record.subjectSummary}
        </p>
      </Section>

      <Section
        label="Linked records"
        description="Every report, entity, and case that accompanied this handoff."
      >
        <div className="grid gap-6 md:grid-cols-3">
          <LinkedList
            label="Reports"
            count={record.linkedReportIds.length}
            ids={record.linkedReportIds}
            hrefPrefix="/strs/"
          />
          <LinkedList
            label="Entities"
            count={record.linkedEntityIds.length}
            ids={record.linkedEntityIds}
            hrefPrefix="/investigate/entity/"
          />
          <LinkedList
            label="Cases"
            count={record.linkedCaseIds.length}
            ids={record.linkedCaseIds}
            hrefPrefix="/cases/"
          />
        </div>
      </Section>
    </div>
  );
}

function LinkedList({
  label,
  count,
  ids,
  hrefPrefix,
}: {
  label: string;
  count: number;
  ids: string[];
  hrefPrefix: string;
}) {
  return (
    <div className="space-y-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label} · <span className="tabular-nums text-foreground">{count}</span>
      </p>
      {ids.length === 0 ? (
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          None
        </p>
      ) : (
        <ul className="divide-y divide-border border border-border">
          {ids.map((id) => (
            <li key={id}>
              <Link
                href={`${hrefPrefix}${id}`}
                className="block px-3 py-2 font-mono text-xs text-accent transition hover:bg-foreground/[0.03]"
              >
                {id.length > 16 ? `${id.slice(0, 4)}··${id.slice(-4)}` : id}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
