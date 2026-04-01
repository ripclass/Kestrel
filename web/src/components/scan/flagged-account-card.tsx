import { Card, CardContent } from "@/components/ui/card";

export function FlaggedAccountCard({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <span>{label}</span>
        <span className="text-primary">{score}</span>
      </CardContent>
    </Card>
  );
}
