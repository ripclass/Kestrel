"use client";

import type { ReactNode } from "react";

export interface CustomerView {
  id: string;
  org_id: string;
  customer_external_id: string;
  customer_type: string;
  full_name: string;
  nid: string | null;
  passport: string | null;
  date_of_birth: string | null;
  nationality: string | null;
  phone: string | null;
  email: string | null;
  address: Record<string, unknown>;
  metadata: Record<string, unknown>;
  beneficial_owners: Array<Record<string, unknown>>;
  risk_score: number | null;
  risk_level: string | null;
  kyc_status: string;
  screening_results: Record<string, unknown>;
  onboarded_at: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
  last_rescreened_at: string | null;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {children}
    </p>
  );
}

export function Section({ eyebrow, children }: { eyebrow: string; children: ReactNode }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <Eyebrow>{eyebrow}</Eyebrow>
      </div>
      {children}
    </section>
  );
}

export function statusTone(status: string | null | undefined): string {
  const value = (status || "").toLowerCase();
  if (value === "declined") return "text-destructive";
  if (value === "review") return "text-accent";
  if (value === "approved") return "text-foreground";
  return "text-muted-foreground";
}

export function riskTone(level: string | null | undefined): string {
  const value = (level || "").toLowerCase();
  if (value === "declined") return "text-destructive";
  if (value === "high") return "text-destructive";
  if (value === "medium") return "text-accent";
  if (value === "low") return "text-foreground";
  return "text-muted-foreground";
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}
