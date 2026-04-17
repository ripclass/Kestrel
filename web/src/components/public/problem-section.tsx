function PatternDiagram() {
  const banks = [
    { label: "Dutch-Bangla", x: 40, y: 50 },
    { label: "City Bank", x: 40, y: 120 },
    { label: "BRAC", x: 40, y: 190 },
    { label: "bKash", x: 40, y: 260 },
    { label: "EBL", x: 40, y: 330 },
    { label: "Nagad", x: 40, y: 400 },
  ];

  return (
    <svg
      role="img"
      aria-label="Six reporting institutions all flag the same entity, but none see each other"
      viewBox="0 0 420 460"
      className="h-auto w-full"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="flowLine" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#58a6a6" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#ef6a5b" stopOpacity="0.9" />
        </linearGradient>
      </defs>

      {banks.map((bank) => (
        <line
          key={`line-${bank.label}`}
          x1={140}
          y1={bank.y}
          x2={320}
          y2={225}
          stroke="url(#flowLine)"
          strokeDasharray="4 4"
          strokeWidth={1}
          opacity={0.55}
        />
      ))}

      {banks.map((bank) => (
        <g key={bank.label}>
          <rect
            x={bank.x}
            y={bank.y - 18}
            width={100}
            height={36}
            rx={8}
            fill="#0f1a2a"
            stroke="#22324b"
          />
          <text
            x={bank.x + 50}
            y={bank.y + 4}
            textAnchor="middle"
            fontSize="11"
            fontFamily="ui-sans-serif, system-ui"
            fill="#ecf2ff"
          >
            {bank.label}
          </text>
        </g>
      ))}

      <circle cx={320} cy={225} r={54} fill="#ef6a5b" opacity={0.08} />
      <circle cx={320} cy={225} r={28} fill="#1a0f11" stroke="#ef6a5b" strokeWidth={1.5} />
      <text
        x={320}
        y={220}
        textAnchor="middle"
        fontSize="10"
        fontFamily="ui-monospace, monospace"
        fill="#fecaca"
      >
        MULE
      </text>
      <text
        x={320}
        y={234}
        textAnchor="middle"
        fontSize="9"
        fontFamily="ui-monospace, monospace"
        fill="#fca5a5"
      >
        account
      </text>

      <text
        x={320}
        y={310}
        textAnchor="middle"
        fontSize="11"
        fontFamily="ui-sans-serif, system-ui"
        fontStyle="italic"
        fill="#94a3b8"
      >
        The pattern nobody sees.
      </text>
    </svg>
  );
}

export function ProblemSection() {
  return (
    <section id="problem" className="border-b border-white/5">
      <div className="mx-auto grid w-full max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-10">
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">The problem</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
            Suspicious activity is reported in isolation. Crime doesn&apos;t work that way.
          </h2>
          <div className="space-y-4 text-base leading-relaxed text-slate-300">
            <p>
              Suspicious transaction reports land in a desktop application whose workflow has
              barely changed since 2006. Analysts review them one at a time. If the same mule
              account was flagged by three banks in the same week, no one sees the pattern — because
              each report lives in its own silo.
            </p>
            <p>
              A modern scammer&apos;s pipeline is fast: a victim transfers funds to a rented account;
              within minutes the money is fanned out across NPSB transfers to wallets at different banks;
              by the time a report is filed, the money is already cash.
            </p>
            <p>
              The gap isn&apos;t effort. BFIU analysts work hard. The gap is infrastructure — nothing in
              the current stack lets them see across institutions in real time.
            </p>
          </div>
        </div>
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm">
          <PatternDiagram />
        </div>
      </div>
    </section>
  );
}
