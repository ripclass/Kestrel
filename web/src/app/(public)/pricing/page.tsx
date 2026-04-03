import { PageFrame } from "@/components/common/page-frame";
import { DeploymentReadinessPanel } from "@/components/public/deployment-readiness";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDeploymentReadiness } from "@/lib/system";

export const dynamic = "force-dynamic";

export default async function PricingPage() {
  const readiness = await fetchDeploymentReadiness();

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-12 lg:px-10">
      <PageFrame
        eyebrow="Cloud-native deployment"
        title="Pricing and rollout posture"
        description="Kestrel ships as a regulator-grade operating stack on Vercel, Render, Supabase, and Redis. Commercial packaging stays flexible, but the runtime envelope is now explicit."
      >
        <div className="grid gap-6 lg:grid-cols-3">
          {[
            ["BFIU command deployment", "National dashboard, shared intelligence, explainable alerts, and regulator-wide RLS visibility."],
            ["Bank intelligence portal", "Bank-scoped scanning, compliance posture, STR drafting, and anonymized network signals."],
            ["Implementation services", "Schema setup, seed tuning, goAML adapter hardening, deployment runbooks, and onboarding support."],
          ].map(([title, detail]) => (
            <Card key={title}>
              <CardHeader>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{detail}</CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle>Runtime envelope</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="flex flex-wrap gap-2">
                <Badge>Next.js on Vercel</Badge>
                <Badge>FastAPI on Render</Badge>
                <Badge>Supabase Postgres/Auth/Storage</Badge>
                <Badge>Redis worker queue</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-primary">Pinned runtimes</p>
                  <p className="mt-2 text-foreground">Node 22.x for web deploys</p>
                  <p className="text-foreground">Python 3.12.8 for engine services</p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-primary">Release gate</p>
                  <p className="mt-2">GitHub CI compiles, tests, builds, then hands off to Vercel and Render production hooks.</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <DeploymentReadinessPanel readiness={readiness} />
        </div>
      </PageFrame>
    </main>
  );
}
