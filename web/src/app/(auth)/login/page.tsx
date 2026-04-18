import Link from "next/link";

import { getActiveDemoPersona, isDemoModeEnabled } from "@/lib/auth";
import { demoPersonaOptions } from "@/lib/demo";
import { LoginForm } from "@/components/auth/login-form";
import { cn } from "@/lib/utils";

export default async function LoginPage() {
  const demoModeEnabled = isDemoModeEnabled();
  const activePersona = demoModeEnabled ? await getActiveDemoPersona() : null;

  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <p className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.3em] text-accent">
          <span aria-hidden className="leading-none">┼</span>
          Secure intake · Authentication
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground lg:text-4xl">
          Sign in to Kestrel
        </h1>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Your workspace, role, and persona resolve from the linked Supabase profile. Provisioning is
          issued to BFIU, banks, MFS providers, and accredited partners.
        </p>
      </div>

      {demoModeEnabled ? (
        <section className="space-y-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Demo mode · Pre-signed personas
          </p>
          <div className="border border-border divide-y divide-border">
            {demoPersonaOptions.map((option) => {
              const isActive = option.persona === activePersona;
              return (
                <Link
                  key={option.persona}
                  href={`/demo/${option.persona}?next=/overview`}
                  className={cn(
                    "flex items-start justify-between gap-4 px-5 py-4 transition",
                    isActive
                      ? "bg-accent/10"
                      : "hover:bg-foreground/[0.03]",
                  )}
                >
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden
                      className={cn(
                        "pt-1 font-mono leading-none",
                        isActive ? "text-accent" : "text-muted-foreground",
                      )}
                    >
                      ┼
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-foreground">{option.title}</p>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                        {option.description}
                      </p>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "mt-0.5 border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em]",
                      isActive
                        ? "border-accent text-accent"
                        : "border-border text-muted-foreground",
                    )}
                  >
                    {isActive ? "Active" : "Launch"}
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="space-y-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Workspace credentials
        </p>
        <LoginForm />
        <div className="flex justify-between font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <Link
            href="/forgot-password"
            className="border-b border-transparent transition hover:border-accent hover:text-accent"
          >
            Forgot password
          </Link>
          <Link
            href="/register"
            className="border-b border-transparent transition hover:border-accent hover:text-accent"
          >
            Request workspace
          </Link>
        </div>
      </section>
    </div>
  );
}
