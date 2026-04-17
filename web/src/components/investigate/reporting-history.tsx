import { Currency } from "@/components/common/currency";
import { RelativeTime } from "@/components/common/relative-time";
import type { ReportingHistoryItem } from "@/types/domain";

export function ReportingHistory({ history }: { history: ReportingHistoryItem[] }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Reporting history
        </p>
      </div>
      {history.length === 0 ? (
        <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          No reports filed against this subject
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-foreground/[0.02]">
                <Th>Reporting org</Th>
                <Th>Reference</Th>
                <Th>Channel</Th>
                <Th className="text-right">Exposure</Th>
                <Th className="text-right">When</Th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.reportRef} className="border-b border-border last:border-b-0">
                  <Td>
                    <span className="text-foreground">{item.orgName}</span>
                  </Td>
                  <Td>
                    <span className="font-mono text-foreground">{item.reportRef}</span>
                  </Td>
                  <Td>
                    <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {item.channel}
                    </span>
                  </Td>
                  <Td className="text-right">
                    <span className="font-mono tabular-nums text-foreground">
                      <Currency amount={item.amount} />
                    </span>
                  </Td>
                  <Td className="text-right">
                    <span className="font-mono text-[11px] text-muted-foreground">
                      <RelativeTime value={item.reportedAt} />
                    </span>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={`px-6 py-3 text-left align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground ${className}`}
    >
      {children}
    </th>
  );
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-6 py-3 align-top ${className}`}>{children}</td>;
}
