"use client";

import { useState } from "react";

import { submitAccessRequest } from "@/app/actions/access";

export function IntakeForm() {
  const [loading, setLoading] = useState(false);
  const [ticketPrinted, setTicketPrinted] = useState(false);
  const [errorPayload, setErrorPayload] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setErrorPayload(null);

    const formData = new FormData(e.currentTarget);
    const res = await submitAccessRequest(formData);

    if (res.success) {
      setTicketPrinted(true);
    } else {
      setErrorPayload(res.message || "Unknown anomaly detected.");
    }
    setLoading(false);
  }

  if (ticketPrinted) {
    return (
      <div className="flex flex-col space-y-4 border border-landing-rule-solid p-8 text-landing-muted">
        <div className="flex items-center justify-between">
          <span className="font-landing-display uppercase tracking-[0.22em] text-landing-foreground">
            Clearance ticket
          </span>
          <span className="text-landing-alarm">┼</span>
        </div>
        <div className="h-px w-full bg-landing-rule-solid" />
        <p className="font-landing-body text-sm uppercase leading-relaxed tracking-[0.12em]">
          Clearance request logged.
          <br />
          Auditable record created.
          <br />
          A clearance officer will contact your designated address.
        </p>
        <span className="mt-8 font-landing-body text-xs uppercase tracking-[0.22em]">
          STATUS · AWAITING_VERIFICATION
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-8">
      <div>
        <h3 className="font-landing-display text-2xl text-landing-foreground">Request clearance</h3>
        <p className="mt-2 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-muted">
          Secure briefing intake protocol
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col space-y-6">
        <div className="flex flex-col space-y-2">
          <label htmlFor="institution" className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
            Institution
          </label>
          <input
            id="institution"
            name="institution"
            required
            className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
            placeholder="Official identity"
          />
        </div>

        <div className="flex flex-col space-y-2">
          <label
            htmlFor="institution_type"
            className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted"
          >
            Institution type
          </label>
          <select
            id="institution_type"
            name="institution_type"
            required
            defaultValue=""
            className="w-full appearance-none rounded-none border border-landing-rule-solid bg-landing-bg px-4 py-3 font-landing-body text-landing-foreground focus:border-landing-foreground focus:outline-none focus:ring-0"
          >
            <option value="" disabled>
              Select classification
            </option>
            <option value="BFIU">BFIU</option>
            <option value="Commercial Bank">Commercial Bank</option>
            <option value="MFS">MFS</option>
            <option value="NBFI">NBFI</option>
            <option value="Peer Regulator">Peer Regulator</option>
            <option value="Press">Press</option>
          </select>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="flex flex-col space-y-2">
            <label
              htmlFor="designation"
              className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted"
            >
              Official designation
            </label>
            <input
              id="designation"
              name="designation"
              required
              className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
              placeholder="e.g. CAMLCO"
            />
          </div>
          <div className="flex flex-col space-y-2">
            <label htmlFor="email" className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Official email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
              placeholder="user@institution.gov.bd"
            />
          </div>
        </div>

        <div className="flex flex-col space-y-2">
          <label htmlFor="use_case" className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
            Intended use (min 50 chars)
          </label>
          <textarea
            id="use_case"
            name="use_case"
            required
            minLength={50}
            rows={4}
            className="w-full resize-none rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
            placeholder="Describe the operational mandate…"
          />
        </div>

        {errorPayload ? (
          <div className="border border-landing-alarm/50 bg-landing-alarm/10 p-3 font-landing-body text-sm uppercase tracking-[0.12em] text-landing-alarm">
            ERROR · {errorPayload}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-2 self-start bg-landing-alarm px-8 py-4 font-landing-display uppercase tracking-[0.22em] text-landing-bg transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Transmitting…" : "Submit request"}
        </button>
      </form>
    </div>
  );
}
