import Link from "next/link";

import { SyntheticBackfillCard } from "@/components/admin/synthetic-backfill-card";
import { PageFrame } from "@/components/common/page-frame";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminSettings, fetchAdminSummary, fetchSyntheticBackfillPlan } from "@/lib/admin";
import { requireRole } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function statusBadge(enabled: boolean, positiveLabel: string, negativeLabel: string) {
  return (
    <Badge
      className={
        enabled
          ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-100"
          : "border-amber-400/30 bg-amber-500/15 text-amber-100"
      }
    >
      {enabled ? positiveLabel : negativeLabel}
    </Badge>
  );
}

export default async function AdminPage() {
  const viewer = await requireRole("manager", "admin", "superadmin");

  let errorMessage: string | null = null;
  let summary: Awaited<ReturnType<typeof fetchAdminSummary>> | null = null;
  let settings: Awaited<ReturnType<typeof fetchAdminSettings>> | null = null;
  let syntheticPlan: Awaited<ReturnType<typeof fetchSyntheticBackfillPlan>> | null = null;

  try {
    [summary, settings] = await Promise.all([fetchAdminSummary(), fetchAdminSettings()]);
    if (viewer.orgType === "regulator" && (viewer.role === "admin" || viewer.role === "superadmin")) {
      syntheticPlan = await fetchSyntheticBackfillPlan();
    }
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "Unable to load administration surfaces.";
  }

  return (
    <PageFrame
      eyebrow="Administration"
      title="Organization settings"
      description={
        errorMessage
          ? "Manage tenant-level configuration, integration posture, and access defaults."
          : "Review tenant posture, integration readiness, and operating controls without leaving the platform."
      }
      actions={
        errorMessage ? undefined : (
          <div className="flex gap-3">
            <Link href="/admin/team">
              <Button variant="outline">Team</Button>
            </Link>
            <Link href="/admin/rules">
              <Button>Rules</Button>
            </Link>
          </div>
        )
      }
    >
      {errorMessage || !summary || !settings ? (
        <ErrorState
          title="Admin settings unavailable"
          description={errorMessage ?? "Unable to load administration surfaces."}
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {[
              ["Team members", `${summary.teamMembers}`, "active user profiles"],
              ["Active rules", `${summary.activeRules}/${summary.totalRules}`, "system and organization overlays"],
              ["API integrations", `${summary.apiIntegrations}`, "configured delivery surfaces"],
              ["Cross-bank hits", `${summary.crossBankHits}`, "visible shared-intelligence reports"],
              ["Detection runs", `${summary.detectionRuns}`, "persisted scan executions"],
            ].map(([label, value, detail]) => (
              <Card key={label}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-muted-foreground">{label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-semibold">{value}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card>
              <CardHeader>
                <CardTitle>{summary.orgName}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-muted-foreground">
                <div className="flex flex-wrap gap-2">
                  <Badge>{summary.orgType}</Badge>
                  <Badge>{summary.plan}</Badge>
                  {summary.syntheticBackfillAvailable ? (
                    <Badge className="border-primary/30 bg-primary/15 text-primary">synthetic backfill ready</Badge>
                  ) : null}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-primary">Auth</p>
                    <div className="mt-3">
                      {statusBadge(settings.authConfigured, "Supabase JWT ready", "Auth config incomplete")}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-primary">Storage</p>
                    <div className="mt-3">
                      {statusBadge(settings.storageConfigured, "Buckets configured", "Bucket config pending")}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-primary">goAML</p>
                    <div className="mt-3">
                      {statusBadge(
                        settings.goamlSyncEnabled && settings.goamlBaseUrlConfigured,
                        "Sync enabled",
                        settings.goamlBaseUrlConfigured ? "Boundary configured" : "Adapter not configured",
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-primary">Runtime</p>
                    <p className="mt-3 text-foreground">
                      {settings.environment} / v{settings.appVersion}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Configuration envelope</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-muted-foreground">
                <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-primary">Buckets</p>
                  <p className="mt-2 text-foreground">{settings.uploadsBucket}</p>
                  <p className="text-foreground">{settings.exportsBucket}</p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-primary">Tenant posture</p>
                  <p className="mt-2">Bank code: {settings.bankCode ?? "Not assigned"}</p>
                  <p>Demo mode: {settings.demoModeEnabled ? "enabled" : "disabled"}</p>
                  <p>Synthetic pack: {settings.syntheticBackfillAvailable ? "available" : "not present"}</p>
                </div>
              </CardContent>
            </Card>
          </div>
          {viewer.orgType === "regulator" && (viewer.role === "admin" || viewer.role === "superadmin") ? (
            <SyntheticBackfillCard initialPlan={syntheticPlan} />
          ) : null}
        </>
      )}
    </PageFrame>
  );
}
