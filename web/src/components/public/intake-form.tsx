"use client";

import { useState } from "react";

import { submitAccessRequest } from "@/app/actions/access";

type AudienceKey = "regulator" | "bfiu" | "press" | "default";

const COMMERCIAL_INSTITUTION_TYPES = [
  "BFIU",
  "Commercial Bank",
  "MFS",
  "NBFI",
  "Peer Regulator",
  "Press",
] as const;

const REGULATOR_INSTITUTION_TYPES = [
  "Financial Intelligence Unit",
  "Central Bank",
  "Supervisory Authority",
  "Other regulator",
] as const;

const DEPLOYMENT_TIMELINES = [
  "Within 3 months",
  "3 to 6 months",
  "6 to 12 months",
  "Over 12 months",
  "Exploratory · timeline undefined",
] as const;

export function IntakeForm({ audience = "default" }: { audience?: AudienceKey }) {
  const [loading, setLoading] = useState(false);
  const [ticketPrinted, setTicketPrinted] = useState(false);
  const [errorPayload, setErrorPayload] = useState<string | null>(null);

  const isRegulator = audience === "regulator";
  const institutionTypeOptions = isRegulator ? REGULATOR_INSTITUTION_TYPES : COMMERCIAL_INSTITUTION_TYPES;

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setErrorPayload(null);

    const formData = new FormData(e.currentTarget);

    if (isRegulator) {
      // Compose regulator-specific fields into use_case for v1 (no schema migration).
      const baseUseCase = (formData.get("use_case")?.toString() ?? "").trim();
      const country = (formData.get("country")?.toString() ?? "").trim();
      const timeline = (formData.get("deployment_timeline")?.toString() ?? "").trim();
      const procurement = (formData.get("procurement_vehicle")?.toString() ?? "").trim();
      const composed = [
        `[Regulator inquiry]`,
        country ? `Country: ${country}` : "",
        timeline ? `Deployment timeline: ${timeline}` : "",
        procurement ? `Procurement vehicle: ${procurement}` : "",
        "",
        baseUseCase,
      ]
        .filter(Boolean)
        .join("\n");
      formData.set("use_case", composed);
      // Drop the audience-specific fields so the server action only sees the canonical schema.
      formData.delete("country");
      formData.delete("deployment_timeline");
      formData.delete("procurement_vehicle");
    }

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
            {isRegulator ? "Proposal request" : "Clearance ticket"}
          </span>
          <span className="text-landing-alarm">┼</span>
        </div>
        <div className="h-px w-full bg-landing-rule-solid" />
        <p className="font-landing-body text-sm uppercase leading-relaxed tracking-[0.12em]">
          {isRegulator ? "Proposal request logged." : "Clearance request logged."}
          <br />
          Auditable record created.
          <br />
          {isRegulator
            ? "A founder will reach out to schedule the briefing."
            : "A clearance officer will contact your designated address."}
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
        <h3 className="font-landing-display text-2xl text-landing-foreground">
          {isRegulator ? "Request a proposal" : "Request clearance"}
        </h3>
        <p className="mt-2 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-muted">
          {isRegulator ? "National-deployment intake protocol" : "Secure briefing intake protocol"}
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
            placeholder={isRegulator ? "e.g. Bangladesh Financial Intelligence Unit" : "Official identity"}
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
            {institutionTypeOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        {isRegulator ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div className="flex flex-col space-y-2">
              <label
                htmlFor="country"
                className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted"
              >
                Country
              </label>
              <input
                id="country"
                name="country"
                required
                defaultValue="Bangladesh"
                className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
              />
            </div>
            <div className="flex flex-col space-y-2">
              <label
                htmlFor="deployment_timeline"
                className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted"
              >
                Deployment timeline
              </label>
              <select
                id="deployment_timeline"
                name="deployment_timeline"
                required
                defaultValue=""
                className="w-full appearance-none rounded-none border border-landing-rule-solid bg-landing-bg px-4 py-3 font-landing-body text-landing-foreground focus:border-landing-foreground focus:outline-none focus:ring-0"
              >
                <option value="" disabled>
                  Select horizon
                </option>
                {DEPLOYMENT_TIMELINES.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : null}

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
              placeholder={isRegulator ? "e.g. Joint Director" : "e.g. CAMLCO"}
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

        {isRegulator ? (
          <div className="flex flex-col space-y-2">
            <label
              htmlFor="procurement_vehicle"
              className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted"
            >
              Procurement vehicle (optional)
            </label>
            <input
              id="procurement_vehicle"
              name="procurement_vehicle"
              className="w-full rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
              placeholder="e.g. Own budget · ADB / World Bank grant · central-bank capex"
            />
          </div>
        ) : null}

        <div className="flex flex-col space-y-2">
          <label htmlFor="use_case" className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
            {isRegulator
              ? "Scope of deployment + anything else to flag (min 50 chars)"
              : "Intended use (min 50 chars)"}
          </label>
          <textarea
            id="use_case"
            name="use_case"
            required
            minLength={50}
            rows={isRegulator ? 5 : 4}
            className="w-full resize-none rounded-none border border-landing-rule-solid bg-transparent px-4 py-3 font-landing-body text-landing-foreground placeholder-landing-muted/50 focus:border-landing-foreground focus:outline-none focus:ring-0"
            placeholder={
              isRegulator
                ? "Describe the deployment scope (FIU only? FIU plus the entire reporting universe?), the existing AML stack, and any procurement constraints we should know about."
                : "Describe the operational mandate…"
            }
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
          {loading
            ? "Transmitting…"
            : isRegulator
              ? "Submit proposal request"
              : "Submit request"}
        </button>
      </form>
    </div>
  );
}
