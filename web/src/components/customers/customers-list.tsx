"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import { CustomerView, Section, fmtDate, riskTone, statusTone } from "@/components/customers/shared";

const STATUS_OPTIONS = [
  { label: "ALL", value: "" },
  { label: "PENDING", value: "pending" },
  { label: "APPROVED", value: "approved" },
  { label: "REVIEW", value: "review" },
  { label: "DECLINED", value: "declined" },
];

const RISK_OPTIONS = [
  { label: "ALL", value: "" },
  { label: "LOW", value: "low" },
  { label: "MEDIUM", value: "medium" },
  { label: "HIGH", value: "high" },
  { label: "DECLINED", value: "declined" },
];

export function CustomersList() {
  const [status, setStatus] = useState<string>("");
  const [risk, setRisk] = useState<string>("");
  const [rows, setRows] = useState<CustomerView[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const handleStatusChange = (value: string) => {
    setLoading(true);
    setError(null);
    setStatus(value);
  };

  const handleRiskChange = (value: string) => {
    setLoading(true);
    setError(null);
    setRisk(value);
  };

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (status) params.set("kyc_status", status);
    if (risk) params.set("risk_level", risk);
    const qs = params.toString() ? `?${params.toString()}` : "";

    fetch(`/api/customers${qs}`, { cache: "no-store" })
      .then(async (r) => {
        const json = await r.json();
        if (!r.ok) throw new Error(json.detail ?? "customers");
        if (!cancelled) setRows((json.rows ?? []) as CustomerView[]);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || "Unable to load customers.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [status, risk]);

  return (
    <div className="space-y-8">
      <Section eyebrow="Filters">
        <div className="flex flex-wrap items-center gap-6 px-6 py-5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">KYC status</span>
            <div className="flex border border-border">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value || "all-status"}
                  type="button"
                  onClick={() => handleStatusChange(opt.value)}
                  className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    status === opt.value ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Risk level</span>
            <div className="flex border border-border">
              {RISK_OPTIONS.map((opt) => (
                <button
                  key={opt.value || "all-risk"}
                  type="button"
                  onClick={() => handleRiskChange(opt.value)}
                  className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    risk === opt.value ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {loading ? (
        <LoadingState label="Resolving customer roster" />
      ) : error ? (
        <ErrorState title="Unable to load customers" description={error} />
      ) : !rows || rows.length === 0 ? (
        <EmptyState
          title="No customers"
          description="Onboard a customer via /customers/new — the screening service runs inline and returns a decision in real time."
        />
      ) : (
        <Section eyebrow={`Customers · ${rows.length}`}>
          <ul className="divide-y divide-border">
            {rows.map((row) => (
              <li key={row.id}>
                <Link
                  href={`/customers/${row.id}`}
                  className="grid grid-cols-12 items-center gap-4 px-6 py-4 transition hover:bg-foreground/[0.03]"
                >
                  <div className="col-span-4 flex flex-col gap-1">
                    <p className="font-mono text-sm text-foreground">{row.full_name}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.customer_external_id} · {row.customer_type}
                    </p>
                  </div>
                  <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {row.nationality ?? "—"}
                    {row.date_of_birth ? ` · DOB ${fmtDate(row.date_of_birth)}` : ""}
                  </div>
                  <div className={`col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] ${riskTone(row.risk_level)}`}>
                    {row.risk_level ? `${row.risk_level} (${row.risk_score ?? "—"})` : "Unscored"}
                  </div>
                  <div className={`col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] ${statusTone(row.kyc_status)}`}>
                    {row.kyc_status}
                  </div>
                  <div className="col-span-2 text-right font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {fmtDate(row.onboarded_at)}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
