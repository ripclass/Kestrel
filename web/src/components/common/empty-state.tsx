export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="border border-border bg-card p-8">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        <span aria-hidden className="mr-2 text-accent">┼</span>
        No records
      </p>
      <h3 className="mt-4 text-lg font-semibold tracking-tight text-foreground">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}
