"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const supabase = createSupabaseBrowserClient();
    if (!supabase) {
      setError("Supabase authentication is not configured for this deployment.");
      return;
    }

    setIsSubmitting(true);
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/login`,
    });
    setIsSubmitting(false);

    if (resetError) {
      setError(resetError.message);
      return;
    }

    setMessage("Password reset instructions were sent if the account exists.");
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <Input
        placeholder="user@institution.gov.bd"
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        autoComplete="email"
      />
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          <span aria-hidden className="mr-2">┼</span>
          ERROR · {error}
        </p>
      ) : null}
      {message ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          {message}
        </p>
      ) : null}
      <Button className="w-full" disabled={isSubmitting || !email} type="submit">
        {isSubmitting ? "Sending…" : "Send reset link"}
      </Button>
    </form>
  );
}
