import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{headline}</p>
        <div className="space-y-2">
          {operational.map((item) => (
            <div key={item} className="rounded-xl border border-border/70 bg-background/50 p-3 text-sm text-muted-foreground">
              {item}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
