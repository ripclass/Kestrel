"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import {
  approveSignupRequest,
  listSignupRequests,
  rejectSignupRequest,
  type SignupRequestRow,
} from "@/app/actions/signup-requests";

const PLAN_IDS = ["starter", "professional", "enterprise", "filing_only"];
const KINDS = ["demo", "pilot", "live"] as const;

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {children}
    </p>
  );
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return "today";
  return `${days}d ago`;
}

function statusTone(status: SignupRequestRow["status"]): string {
  if (status === "pending") return "text-accent";
  if (status === "rejected") return "text-destructive";
  return "text-foreground";
}

const fieldClass =
  "border border-border bg-background px-3 py-2 font-mono text-xs text-foreground";

function PendingCard({
  request,
  onDecided,
}: {
  request: SignupRequestRow;
  onDecided: () => void;
}) {
  const [planId, setPlanId] = useState("professional");
  const [kind, setKind] = useState<(typeof KINDS)[number]>("pilot");
  const [seed, setSeed] = useState(true);
  const [note, setNote] = useState("");
  const [working, setWorking] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approve" | "reject") {
    setWorking(decision);
    setError(null);
    try {
      const result =
        decision === "approve"
          ? await approveSignupRequest({
              requestId: request.id,
              planId,
              tenantKind: kind,
              seedDemoData: seed,
              note,
            })
          : await rejectSignupRequest(request.id, note);
      if (!result.success) {
        setError(result.message ?? "Decision failed.");
        return;
      }
      if (result.message) {
        setError(result.message);
      }
      onDecided();
    } catch {
      setError("Decision failed — unexpected error.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <li className="space-y-4 px-6 py-5">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <span className="text-sm text-foreground">{request.bank_name}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          {request.full_name} · {request.designation}
        </span>
        <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {relativeTime(request.created_at)}
        </span>
      </div>
      <p className="font-mono text-xs text-muted-foreground">
        {request.email}
        {request.phone ? ` · ${request.phone}` : ""}
      </p>
      <p className="border border-border px-4 py-3 text-sm leading-relaxed text-foreground/85">
        {request.demo_narrative}
      </p>

      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Plan
          </span>
          <select
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            className={fieldClass}
          >
            {PLAN_IDS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Classification
          </span>
          <div className="flex border border-border">
            {KINDS.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`px-3 py-2 font-mono text-[10px] uppercase tracking-[0.22em] transition ${
                  kind === k
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {k}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 pb-2">
          <input
            type="checkbox"
            checked={seed}
            onChange={(e) => setSeed(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Seed demo data
          </span>
        </label>
        <label className="flex min-w-48 flex-1 flex-col gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Decision note (optional)
          </span>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Verified against BB scheduled-bank list"
            className={fieldClass}
          />
        </label>
      </div>

      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ {error}
        </p>
      ) : null}

      <div className="flex gap-3">
        <button
          type="button"
          disabled={working !== null}
          onClick={() => decide("approve")}
          className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
        >
          {working === "approve" ? "Provisioning…" : "Approve + provision"}
        </button>
        <button
          type="button"
          disabled={working !== null}
          onClick={() => decide("reject")}
          className="border border-border px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition hover:border-destructive hover:text-destructive disabled:opacity-50"
        >
          {working === "reject" ? "Rejecting…" : "Reject"}
        </button>
      </div>
    </li>
  );
}

export function SignupRequests() {
  const [requests, setRequests] = useState<SignupRequestRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const result = await listSignupRequests();
      if (!result.success || !result.requests) {
        throw new Error(result.message ?? "Unable to load signup requests.");
      }
      setRequests(result.requests);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load signup requests.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading && !requests) {
    return <LoadingState label="Loading signup requests" />;
  }
  if (!requests) {
    return <ErrorState title="Unable to load signup requests" description={error ?? "—"} />;
  }

  const pending = requests.filter((r) => r.status === "pending");
  const decided = requests.filter((r) => r.status !== "pending");

  return (
    <div className="space-y-6">
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ ERROR · {error}
        </p>
      ) : null}

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <Eyebrow>Pending review · {pending.length}</Eyebrow>
        </div>
        {pending.length === 0 ? (
          <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            No pending requests
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {pending.map((request) => (
              <PendingCard key={request.id} request={request} onDecided={refresh} />
            ))}
          </ul>
        )}
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <Eyebrow>Decided · {decided.length}</Eyebrow>
        </div>
        {decided.length === 0 ? (
          <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            No decisions yet
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {decided.map((request) => (
              <li key={request.id} className="px-6 py-4">
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
                  <span className="text-sm text-foreground">{request.bank_name}</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    {request.email}
                  </span>
                  <span
                    className={`font-mono text-[10px] uppercase tracking-[0.2em] ${statusTone(request.status)}`}
                  >
                    ● {request.status}
                  </span>
                  <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    {request.decided_by ?? "—"} · {relativeTime(request.decided_at)}
                  </span>
                </div>
                {request.decision_note ? (
                  <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                    {request.decision_note}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        ┼ Approval provisions the organization and emails the requester a
        magic-link admin invite — same path as console tenant provisioning.
        Verify the institution against the Bangladesh Bank scheduled-bank list
        and the email domain before approving.
      </p>
    </div>
  );
}
