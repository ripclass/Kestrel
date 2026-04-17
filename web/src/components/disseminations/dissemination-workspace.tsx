"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DisseminationDetail } from "@/types/domain";

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
      <Card>
        <CardContent className="py-10 text-sm text-red-300">{error}</CardContent>
      </Card>
    );
  }
  if (!record) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Loading dissemination…</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle>{record.disseminationRef}</CardTitle>
              <CardDescription>
                {record.recipientAgency} · {record.classification}
              </CardDescription>
            </div>
            <Link
              href="/intelligence/disseminations"
              className="text-sm text-muted-foreground hover:text-primary"
            >
              ← Back to disseminations
            </Link>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recipient</p>
            <p className="mt-1 text-sm font-medium">{record.recipientAgency}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recipient type</p>
            <p className="mt-1 text-sm font-medium">{record.recipientType.replace("_", " ")}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Classification</p>
            <p className="mt-1 text-sm font-medium">{record.classification}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Disseminated</p>
            <p className="mt-1 text-sm font-medium">{new Date(record.disseminatedAt).toLocaleString()}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subject summary</CardTitle>
          <CardDescription>The narrative sent alongside the underlying reports and entities.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm">{record.subjectSummary}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Linked records</CardTitle>
          <CardDescription>Every report, entity, and case that accompanied this handoff.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Reports ({record.linkedReportIds.length})</p>
            <ul className="space-y-1 text-sm">
              {record.linkedReportIds.length === 0 ? (
                <li className="text-muted-foreground">None</li>
              ) : (
                record.linkedReportIds.map((id) => (
                  <li key={id}>
                    <Link href={`/strs/${id}`} className="text-primary hover:underline">
                      {id}
                    </Link>
                  </li>
                ))
              )}
            </ul>
          </div>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Entities ({record.linkedEntityIds.length})</p>
            <ul className="space-y-1 text-sm">
              {record.linkedEntityIds.length === 0 ? (
                <li className="text-muted-foreground">None</li>
              ) : (
                record.linkedEntityIds.map((id) => (
                  <li key={id}>
                    <Link href={`/investigate/entity/${id}`} className="text-primary hover:underline">
                      {id}
                    </Link>
                  </li>
                ))
              )}
            </ul>
          </div>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Cases ({record.linkedCaseIds.length})</p>
            <ul className="space-y-1 text-sm">
              {record.linkedCaseIds.length === 0 ? (
                <li className="text-muted-foreground">None</li>
              ) : (
                record.linkedCaseIds.map((id) => (
                  <li key={id}>
                    <Link href={`/cases/${id}`} className="text-primary hover:underline">
                      {id}
                    </Link>
                  </li>
                ))
              )}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
