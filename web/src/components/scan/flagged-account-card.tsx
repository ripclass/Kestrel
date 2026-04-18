import Link from "next/link";

import { Currency } from "@/components/common/currency";
import { RiskScore } from "@/components/common/risk-score";
import type { FlaggedAccount } from "@/types/domain";

export function FlaggedAccountCard({ account }: { account: FlaggedAccount }) {
  return (
    <article className="space-y-4 border border-border bg-card p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <p className="text-base font-semibold text-foreground">{account.accountName}</p>
          <p className="font-mono text-sm text-muted-foreground">{account.accountNumber}</p>
        </div>
        <RiskScore score={account.score} severity={account.severity} />
      </div>
      <p className="text-sm leading-relaxed text-foreground">{account.summary}</p>
      <div className="flex flex-wrap gap-2">
        <span className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          <span className="tabular-nums text-foreground">{account.matchedBanks}</span> banks
        </span>
        <span className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Exposure ·{" "}
          <span className="tabular-nums text-foreground">
            <Currency amount={account.totalExposure} />
          </span>
        </span>
        {account.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            {tag.replaceAll("_", " ")}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap gap-4 border-t border-border pt-4 font-mono text-[11px] uppercase tracking-[0.22em]">
        <Link
          href={`/investigate/entity/${account.entityId}`}
          className="text-accent transition hover:text-foreground"
        >
          Open entity →
        </Link>
        {account.linkedAlertId ? (
          <Link
            href={`/alerts/${account.linkedAlertId}`}
            className="text-accent transition hover:text-foreground"
          >
            Open alert →
          </Link>
        ) : null}
        {account.linkedCaseId ? (
          <Link
            href={`/cases/${account.linkedCaseId}`}
            className="text-accent transition hover:text-foreground"
          >
            Open case →
          </Link>
        ) : null}
      </div>
    </article>
  );
}
