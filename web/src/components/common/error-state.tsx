import { Button } from "@/components/ui/button";

export function ErrorState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="border border-destructive/40 bg-destructive/5 p-8">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>
        Anomaly · Unable to load
      </p>
      <h3 className="mt-4 text-lg font-semibold tracking-tight text-foreground">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
      <div className="mt-6">
        <Button variant="outline">Retry</Button>
      </div>
    </div>
  );
}
