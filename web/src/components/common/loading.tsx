export function LoadingState({ label = "Loading Kestrel intelligence…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 border border-border bg-card px-5 py-8 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
      <span aria-hidden className="leading-none text-accent">┼</span>
      <span>{label}</span>
    </div>
  );
}
