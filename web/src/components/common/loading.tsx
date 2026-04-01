export function LoadingState({ label = "Loading Kestrel intelligence..." }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-border/80 bg-card/60 px-5 py-8 text-sm text-muted-foreground">
      {label}
    </div>
  );
}
