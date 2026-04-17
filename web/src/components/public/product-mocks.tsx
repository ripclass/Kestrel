export function DossierMock() {
  const reports = [
    { bank: "Dutch-Bangla Bank", kind: "STR", tone: "rose" },
    { bank: "City Bank", kind: "STR", tone: "rose" },
    { bank: "BRAC Bank", kind: "SAR", tone: "amber" },
    { bank: "bKash", kind: "Complaint", tone: "amber" },
  ];
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1524] p-5">
      <div className="flex items-center justify-between border-b border-white/5 pb-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
            entity dossier
          </p>
          <p className="mt-1 font-mono text-sm text-white">account · 112··3847</p>
        </div>
        <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] text-rose-200">
          risk 87
        </span>
      </div>
      <ul className="mt-4 space-y-2">
        {reports.map((report) => (
          <li
            key={`${report.bank}-${report.kind}`}
            className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-sm"
          >
            <span className="text-slate-200">{report.bank}</span>
            <span
              className={`font-mono text-[10px] uppercase tracking-wider ${
                report.tone === "rose" ? "text-rose-200" : "text-amber-200"
              }`}
            >
              {report.kind}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] text-slate-400">
        4 reports · 3 banks · first flagged 2026-02-11
      </p>
    </div>
  );
}

export function NetworkMock() {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1524] p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
          network · 2-hop
        </p>
        <p className="font-mono text-[10px] text-slate-400">18 nodes · 24 edges</p>
      </div>
      <svg
        viewBox="0 0 400 240"
        className="h-auto w-full"
        role="img"
        aria-label="Two-hop network graph surrounding a flagged subject"
      >
        {[
          [80, 60],
          [320, 60],
          [60, 180],
          [340, 180],
          [200, 30],
          [200, 210],
          [140, 120],
          [260, 120],
        ].map(([x, y], i) => (
          <line
            key={i}
            x1={200}
            y1={120}
            x2={x}
            y2={y}
            stroke="#58a6a6"
            strokeOpacity={0.35}
            strokeWidth={1}
          />
        ))}
        {[
          [80, 60, "A"],
          [320, 60, "B"],
          [60, 180, "C"],
          [340, 180, "D"],
          [200, 30, "E"],
          [200, 210, "F"],
          [140, 120, "G"],
          [260, 120, "H"],
        ].map(([x, y, label]) => (
          <g key={`${x}-${y}`}>
            <circle cx={x as number} cy={y as number} r={12} fill="#0f1a2a" stroke="#58a6a6" />
            <text
              x={x as number}
              y={(y as number) + 3}
              textAnchor="middle"
              fontSize="9"
              fontFamily="ui-monospace, monospace"
              fill="#ecf2ff"
            >
              {label}
            </text>
          </g>
        ))}
        <circle cx={200} cy={120} r={54} fill="#ef6a5b" opacity={0.08} />
        <circle cx={200} cy={120} r={18} fill="#1a0f11" stroke="#ef6a5b" strokeWidth={1.5} />
        <text
          x={200}
          y={123}
          textAnchor="middle"
          fontSize="10"
          fontFamily="ui-monospace, monospace"
          fill="#fecaca"
        >
          SUBJ
        </text>
      </svg>
    </div>
  );
}

export function ExplanationMock() {
  const rules = [
    { code: "rapid_cashout", weight: 34, hit: true },
    { code: "fan_out_burst", weight: 28, hit: true },
    { code: "cross_bank_match", weight: 22, hit: true },
    { code: "first_time_high_value", weight: 16, hit: true },
  ];
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1524] p-5">
      <div className="flex items-center justify-between border-b border-white/5 pb-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
            alert explanation
          </p>
          <p className="mt-1 text-sm text-white">Why did Kestrel flag this?</p>
        </div>
        <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[10px] text-primary">
          score 87
        </span>
      </div>
      <ul className="mt-4 space-y-2">
        {rules.map((rule) => (
          <li key={rule.code} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-slate-200">{rule.code}</span>
              <span className="font-mono text-slate-400">{rule.weight}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${rule.weight * 2.4}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[11px] leading-relaxed text-slate-400">
        Every hit links to the exact transactions, timestamps, and amounts that triggered it — audit-ready before an analyst opens it.
      </p>
    </div>
  );
}
