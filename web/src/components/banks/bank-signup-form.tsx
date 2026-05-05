"use client";

import { useState } from "react";

import { submitBankSignup } from "@/app/actions/bank-signup";

export function BankSignupForm() {
  const [loading, setLoading] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(event.currentTarget);
    const result = await submitBankSignup(formData);

    if (result.success) {
      setSubmittedEmail(result.email ?? null);
    } else {
      setError(result.message ?? "Unknown anomaly during signup.");
    }
    setLoading(false);
  }

  if (submittedEmail) {
    return (
      <div className="flex flex-col gap-5 border border-landing-rule-solid p-8 text-landing-foreground">
        <div className="flex items-center justify-between">
          <span className="font-landing-display uppercase tracking-[0.22em]">
            Workspace provisioned
          </span>
          <span className="text-landing-alarm">┼</span>
        </div>
        <div className="h-px w-full bg-landing-rule-solid" />
        <div className="space-y-3 font-landing-body text-sm leading-relaxed text-landing-foreground/85">
          <p>
            Magic-link invitation sent to <span className="text-landing-alarm">{submittedEmail}</span>.
          </p>
          <p className="text-landing-foreground/70">
            Open the email, accept the invite, and you land on the bank dashboard at
            <span className="font-landing-body uppercase tracking-[0.18em]"> /overview</span>. A demo
            tenant of synthetic transactions is being prepared in the background and lights up after
            first sign-in.
          </p>
        </div>
        <span className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-muted">
          STATUS · INVITE_DISPATCHED · AWAITING_FIRST_LOGIN
        </span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Field label="Bank name" htmlFor="bank_name">
          <input
            id="bank_name"
            name="bank_name"
            required
            placeholder="e.g. BRAC Bank PLC"
            className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
          />
        </Field>
        <Field label="Full name" htmlFor="full_name">
          <input
            id="full_name"
            name="full_name"
            required
            placeholder="Official identity"
            className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Field label="Role / designation" htmlFor="role">
          <input
            id="role"
            name="role"
            required
            placeholder="e.g. CAMLCO, Head of Compliance"
            className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
          />
        </Field>
        <Field label="Phone (optional)" htmlFor="phone">
          <input
            id="phone"
            name="phone"
            placeholder="+880 1XXX-XXXXXX"
            className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
          />
        </Field>
      </div>

      <Field label="Official email" htmlFor="email">
        <input
          id="email"
          name="email"
          type="email"
          required
          placeholder="user@institution.gov.bd"
          className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
        />
      </Field>

      <Field label="What would you like to see in the demo? (min 30 chars)" htmlFor="demo_narrative">
        <textarea
          id="demo_narrative"
          name="demo_narrative"
          required
          minLength={30}
          rows={4}
          placeholder="e.g. Run cross-bank intelligence on a structuring case spanning bKash and an NPSB partner; produce a draft STR ready for submission."
          className="w-full resize-none rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
        />
      </Field>

      {error ? (
        <div className="border border-landing-alarm/50 bg-landing-alarm/10 p-3 font-landing-body text-sm uppercase tracking-[0.12em] text-landing-alarm">
          ERROR · {error}
        </div>
      ) : null}

      <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="submit"
          disabled={loading}
          className="self-start bg-landing-alarm px-8 py-4 font-landing-display uppercase tracking-[0.22em] text-landing-bg transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Provisioning…" : "Provision workspace"}
        </button>
        <p className="font-landing-body text-[10px] uppercase tracking-[0.24em] text-landing-muted">
          ┼ Magic link · No password to remember
        </p>
      </div>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className="flex flex-col gap-2">
      <span className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
        {label}
      </span>
      {children}
    </label>
  );
}
