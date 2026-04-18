export function OverviewBrief({
  title,
  headline,
  operational,
}: {
  title: string;
  headline: string;
  operational: string[];
}) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {title}
        </p>
        <p className="mt-3 text-base leading-relaxed text-foreground">{headline}</p>
      </div>
      <ul className="divide-y divide-border">
        {operational.map((item, i) => (
          <li
            key={item}
            className="flex items-start gap-4 px-6 py-4 text-sm leading-relaxed text-foreground"
          >
            <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
