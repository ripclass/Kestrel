import Link from "next/link";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <p className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.3em] text-accent">
          <span aria-hidden className="leading-none">┼</span>
          Credential recovery
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground lg:text-4xl">
          Reset password
        </h1>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Kestrel uses Supabase Auth email recovery. Submit your account email to trigger reset
          instructions. The instructions arrive only if the account exists.
        </p>
      </div>

      <section className="space-y-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Account email
        </p>
        <ForgotPasswordForm />
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <Link
            href="/login"
            className="border-b border-transparent transition hover:border-accent hover:text-accent"
          >
            ← Return to sign-in
          </Link>
        </p>
      </section>
    </div>
  );
}
