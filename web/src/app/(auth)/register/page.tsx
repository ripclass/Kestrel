import Link from "next/link";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function RegisterPage() {
  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <p className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.3em] text-accent">
          <span aria-hidden className="leading-none">┼</span>
          Workspace provisioning
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground lg:text-4xl">
          Register a bank workspace
        </h1>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Banks continue to file in goAML. This flow scaffolds Kestrel access, scan onboarding, and
          peer-network posture visibility. Access is issued after clearance review.
        </p>
      </div>

      <form className="space-y-5">
        <Field label="Organisation name">
          <Input placeholder="e.g. Dutch-Bangla Bank Ltd." />
        </Field>
        <Field label="Full name">
          <Input placeholder="Official identity" />
        </Field>
        <Field label="Official email">
          <Input placeholder="user@institution.gov.bd" type="email" />
        </Field>
        <Field label="Password">
          <Input placeholder="••••••••" type="password" />
        </Field>
        <Button className="w-full" type="button">
          Create access request
        </Button>
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Already provisioned?{" "}
          <Link
            href="/login"
            className="border-b border-transparent text-accent transition hover:border-accent"
          >
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}
