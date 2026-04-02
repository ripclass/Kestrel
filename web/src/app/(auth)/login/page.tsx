import Link from "next/link";

import { getActiveDemoPersona, isDemoModeEnabled } from "@/lib/auth";
import { demoPersonaOptions } from "@/lib/demo";
import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default async function LoginPage() {
  const demoModeEnabled = isDemoModeEnabled();
  const activePersona = demoModeEnabled ? await getActiveDemoPersona() : null;

  return (
    <div className="space-y-6">
      {demoModeEnabled ? (
        <Card>
          <CardHeader>
            <CardTitle>Choose a demo persona</CardTitle>
            <CardDescription>
              This deployment is running in scaffold demo mode. Switch personas without changing env vars or redeploying.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {demoPersonaOptions.map((option) => (
              <Link
                key={option.persona}
                href={`/demo/${option.persona}?next=/overview`}
                className={cn(
                  "rounded-2xl border border-border/70 bg-card/70 p-4 transition hover:border-primary/50 hover:bg-card",
                  option.persona === activePersona ? "border-primary bg-primary/10" : "",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-base font-semibold">{option.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{option.description}</p>
                  </div>
                  <span className="rounded-full border border-border/70 px-3 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    {option.persona === activePersona ? "active" : "launch"}
                  </span>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>Log in to Kestrel</CardTitle>
          <CardDescription>
            Sign in with your provisioned Kestrel workspace credentials. Org, role, and persona are resolved from the linked Supabase profile.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <LoginForm />
          <div className="flex justify-between text-sm text-muted-foreground">
            <Link href="/forgot-password">Forgot password</Link>
            <Link href="/register">Register bank access</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
