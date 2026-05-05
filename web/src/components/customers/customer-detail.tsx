"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import { CustomerView, Section, fmtDate, riskTone, statusTone } from "@/components/customers/shared";

interface ScreeningHit {
  list_source: string;
  list_version: string;
  matched_name: string;
  match_score: number;
  match_reasons: string[];
}

export function CustomerDetail({ customerId }: { customerId: string }) {
  const [customer, setCustomer] = useState<CustomerView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionPending, setActionPending] = useState(false);

  const refresh = async () => {
    setError(null);
    try {
      const r = await fetch(`/api/customers/${encodeURIComponent(customerId)}`, { cache: "no-store" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "customer");
      setCustomer(json as CustomerView);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load customer.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  const review = async (decision: "approved" | "declined" | "review") => {
    setActionPending(true);
    setError(null);
    try {
      const r = await fetch(`/api/customers/${encodeURIComponent(customerId)}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "review");
      setCustomer(json as CustomerView);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to record review.");
    } finally {
      setActionPending(false);
    }
  };

  const rescreen = async () => {
    setActionPending(true);
    setError(null);
    try {
      const r = await fetch(`/api/customers/${encodeURIComponent(customerId)}/rescreen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "rescreen");
      setCustomer(json as CustomerView);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to rescreen customer.");
    } finally {
      setActionPending(false);
    }
  };

  if (loading) return <LoadingState label="Resolving customer" />;
  if (error && !customer) return <ErrorState title="Unable to load customer" description={error} />;
  if (!customer) return <ErrorState title="Not found" description="Customer record could not be loaded." />;

  const primaryHits = (customer.screening_results.primary as ScreeningHit[] | undefined) ?? [];
  const boHits =
    (customer.screening_results.beneficial_owners as Record<string, ScreeningHit[]> | undefined) ?? {};

  return (
    <div className="space-y-8">
      <Section eyebrow={`Profile · ${customer.customer_external_id}`}>
        <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-3">
          <Tile label="Risk score" value={`${customer.risk_score ?? "—"}`} tone={riskTone(customer.risk_level)} />
          <Tile label="Risk level" value={(customer.risk_level || "Unscored").toUpperCase()} tone={riskTone(customer.risk_level)} />
          <Tile label="KYC status" value={customer.kyc_status.toUpperCase()} tone={statusTone(customer.kyc_status)} />
        </div>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 px-6 py-6 md:grid-cols-2">
          <Pair label="Full name" value={customer.full_name} />
          <Pair label="Type" value={customer.customer_type} />
          <Pair label="Nationality" value={customer.nationality ?? "—"} />
          <Pair label="Date of birth" value={fmtDate(customer.date_of_birth)} />
          <Pair label="NID" value={customer.nid ?? "—"} />
          <Pair label="Passport" value={customer.passport ?? "—"} />
          <Pair label="Phone" value={customer.phone ?? "—"} />
          <Pair label="Email" value={customer.email ?? "—"} />
          <Pair label="Onboarded" value={fmtDate(customer.onboarded_at)} />
          <Pair label="Last rescreened" value={fmtDate(customer.last_rescreened_at)} />
          <Pair label="Reviewed" value={fmtDate(customer.reviewed_at)} />
        </dl>
      </Section>

      <Section eyebrow={`Primary screening · ${primaryHits.length} hit${primaryHits.length === 1 ? "" : "s"}`}>
        {primaryHits.length === 0 ? (
          <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            No matches against the shared sanctions / PEP pool.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {primaryHits.map((hit, idx) => (
              <li key={idx} className="grid grid-cols-12 items-start gap-4 px-6 py-4">
                <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground">
                  {hit.list_source}
                </div>
                <div className={`col-span-1 text-right font-mono text-lg tabular-nums ${hit.match_score >= 0.9 ? "text-destructive" : "text-accent"}`}>
                  {hit.match_score.toFixed(2)}
                </div>
                <div className="col-span-5 font-mono text-sm text-foreground">{hit.matched_name}</div>
                <div className="col-span-4 flex flex-col gap-1">
                  {hit.match_reasons.map((r, ridx) => (
                    <p key={ridx} className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      ┼ {r}
                    </p>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {customer.beneficial_owners.length > 0 ? (
        <Section eyebrow={`Beneficial owners · ${customer.beneficial_owners.length}`}>
          <ul className="divide-y divide-border">
            {customer.beneficial_owners.map((bo, idx) => {
              const name = String(bo.full_name ?? "—");
              const hits = boHits[name] ?? [];
              return (
                <li key={idx} className="space-y-2 px-6 py-4">
                  <div className="flex flex-wrap items-center gap-4">
                    <p className="font-mono text-sm text-foreground">{name}</p>
                    {bo.ownership_pct !== undefined && bo.ownership_pct !== null ? (
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                        {String(bo.ownership_pct)}% ownership
                      </p>
                    ) : null}
                    {bo.nationality ? (
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                        {String(bo.nationality)}
                      </p>
                    ) : null}
                  </div>
                  {hits.length === 0 ? (
                    <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      ┼ Clean — no watchlist match.
                    </p>
                  ) : (
                    <ul className="space-y-1">
                      {hits.map((hit, hi) => (
                        <li key={hi} className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
                          ┼ {hit.list_source} · {hit.matched_name} · {hit.match_score.toFixed(2)}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </Section>
      ) : null}

      <Section eyebrow="Review actions">
        <div className="flex flex-wrap items-center gap-3 px-6 py-5">
          <button
            type="button"
            onClick={() => review("approved")}
            disabled={actionPending}
            className="border border-foreground bg-foreground px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => review("review")}
            disabled={actionPending}
            className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background disabled:opacity-50"
          >
            Send to review
          </button>
          <button
            type="button"
            onClick={() => review("declined")}
            disabled={actionPending}
            className="border border-destructive px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-destructive transition hover:bg-destructive hover:text-background disabled:opacity-50"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={rescreen}
            disabled={actionPending}
            className="ml-auto border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:bg-accent hover:text-background disabled:opacity-50"
          >
            {actionPending ? "Working…" : "Re-run screening"}
          </button>
        </div>
        {error ? (
          <p className="px-6 pb-5 font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            ┼ ERROR · {error}
          </p>
        ) : null}
      </Section>
    </div>
  );
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</dt>
      <dd className="font-mono text-sm text-foreground">{value}</dd>
    </div>
  );
}

function Tile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex flex-col gap-2 border border-border p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
      <p className={`font-mono text-3xl tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}
