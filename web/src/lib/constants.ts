export const severityColorMap = {
  critical: "text-red-300 bg-red-500/15 border-red-400/30",
  high: "text-amber-300 bg-amber-500/15 border-amber-400/30",
  medium: "text-sky-300 bg-sky-500/15 border-sky-400/30",
  low: "text-emerald-300 bg-emerald-500/15 border-emerald-400/30",
} as const;

export const channelCatalog = [
  "RTGS",
  "BEFTN",
  "NPSB",
  "MFS",
  "Cash",
  "Card",
] as const;

export const riskThresholds = {
  critical: 90,
  high: 70,
  medium: 45,
};
