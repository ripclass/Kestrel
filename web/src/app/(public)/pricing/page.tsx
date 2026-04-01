import { PageFrame } from "@/components/common/page-frame";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PricingPage() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-12 lg:px-10">
      <PageFrame
        eyebrow="Cloud-native deployment"
        title="Pricing and rollout posture"
        description="Kestrel is scaffolded for Vercel, Render, and Supabase. The commercial model is intentionally left open while the product and deployment shape are finalized."
      >
        <div className="grid gap-6 lg:grid-cols-3">
          {[
            ["BFIU command deployment", "National command view, intelligence engine, regulator-wide access controls."],
            ["Bank intelligence portal", "Bank-scoped scanning, posture dashboards, and anonymized network signals."],
            ["Implementation services", "Schema setup, seed tuning, goAML adapter hardening, and production rollout support."],
          ].map(([title, detail]) => (
            <Card key={title}>
              <CardHeader>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{detail}</CardContent>
            </Card>
          ))}
        </div>
      </PageFrame>
    </main>
  );
}
