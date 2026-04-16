import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AiExplanation as AiExplanationModel } from "@/types/domain";

export function AiExplanation({
  explanation,
  isLoading,
  error,
}: {
  explanation: AiExplanationModel | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Generating explanation...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !explanation) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium">Summary</p>
          <p className="mt-1 text-sm text-muted-foreground">{explanation.summary}</p>
        </div>
        <div>
          <p className="text-sm font-medium">Why it matters</p>
          <p className="mt-1 text-sm text-muted-foreground">{explanation.whyItMatters}</p>
        </div>
        {explanation.recommendedActions.length > 0 ? (
          <div>
            <p className="text-sm font-medium">Recommended actions</p>
            <ul className="mt-1 list-disc pl-5 text-sm text-muted-foreground">
              {explanation.recommendedActions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
