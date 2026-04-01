import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TypologySummary } from "@/types/domain";

export function TypologyCard({ typology }: { typology: TypologySummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{typology.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>{typology.narrative}</p>
        <div className="flex flex-wrap gap-2">
          {typology.indicators.map((indicator) => (
            <span key={indicator} className="rounded-full bg-white/5 px-3 py-1 text-xs">
              {indicator}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
