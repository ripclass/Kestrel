export function NetworkIllustration({ className }: { className?: string }) {
  const outerNodes = [
    { id: "b1", label: "Bank A", x: 60, y: 60 },
    { id: "b2", label: "Bank B", x: 260, y: 40 },
    { id: "b3", label: "Bank C", x: 430, y: 100 },
    { id: "b4", label: "Bank D", x: 440, y: 280 },
    { id: "b5", label: "Bank E", x: 240, y: 340 },
    { id: "b6", label: "Bank F", x: 60, y: 260 },
  ];
  const centerX = 250;
  const centerY = 190;

  return (
    <svg
      role="img"
      aria-label="Network graph showing six banks reporting into a shared flagged entity"
      viewBox="0 0 500 380"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="flaggedGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ef6a5b" stopOpacity="0.55" />
          <stop offset="70%" stopColor="#ef6a5b" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="edge" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#58a6a6" stopOpacity="0.1" />
          <stop offset="50%" stopColor="#58a6a6" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#ef6a5b" stopOpacity="0.9" />
        </linearGradient>
      </defs>

      {outerNodes.map((node) => (
        <line
          key={`edge-${node.id}`}
          x1={node.x}
          y1={node.y}
          x2={centerX}
          y2={centerY}
          stroke="url(#edge)"
          strokeWidth={1.5}
        />
      ))}

      <circle cx={centerX} cy={centerY} r={58} fill="url(#flaggedGlow)" />
      <circle
        cx={centerX}
        cy={centerY}
        r={22}
        fill="#1a0f11"
        stroke="#ef6a5b"
        strokeWidth={1.5}
      />
      <text
        x={centerX}
        y={centerY + 4}
        textAnchor="middle"
        fontSize="10"
        fontFamily="ui-monospace, monospace"
        fill="#fecaca"
      >
        FLAGGED
      </text>

      {outerNodes.map((node) => (
        <g key={node.id}>
          <circle
            cx={node.x}
            cy={node.y}
            r={16}
            fill="#0f1a2a"
            stroke="#58a6a6"
            strokeWidth={1.2}
            opacity={0.95}
          />
          <text
            x={node.x}
            y={node.y + 4}
            textAnchor="middle"
            fontSize="9"
            fontFamily="ui-monospace, monospace"
            fill="#ecf2ff"
          >
            {node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
