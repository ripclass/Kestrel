"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CustomerView, Section, riskTone, statusTone } from "@/components/customers/shared";

interface BeneficialOwnerInput {
  full_name: string;
  nid: string;
  passport: string;
  date_of_birth: string;
  nationality: string;
  ownership_pct: string;
}

const emptyOwner = (): BeneficialOwnerInput => ({
  full_name: "",
  nid: "",
  passport: "",
  date_of_birth: "",
  nationality: "",
  ownership_pct: "",
});

export function CustomerOnboardForm() {
  const router = useRouter();
  const [externalId, setExternalId] = useState("");
  const [type, setType] = useState<"individual" | "business">("individual");
  const [fullName, setFullName] = useState("");
  const [nid, setNid] = useState("");
  const [passport, setPassport] = useState("");
  const [dob, setDob] = useState("");
  const [nationality, setNationality] = useState("BD");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("Dhaka");
  const [country, setCountry] = useState("Bangladesh");
  const [owners, setOwners] = useState<BeneficialOwnerInput[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CustomerView | null>(null);

  const addOwner = () => setOwners([...owners, emptyOwner()]);
  const removeOwner = (idx: number) => setOwners(owners.filter((_, i) => i !== idx));
  const updateOwner = (idx: number, patch: Partial<BeneficialOwnerInput>) => {
    setOwners(owners.map((o, i) => (i === idx ? { ...o, ...patch } : o)));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!externalId.trim() || !fullName.trim()) {
      setError("Customer external ID and full name are required.");
      return;
    }
    setSubmitting(true);

    const payload: Record<string, unknown> = {
      customer_external_id: externalId.trim(),
      customer_type: type,
      full_name: fullName.trim(),
      address: { city: city || null, country: country || null },
    };
    if (nid.trim()) payload.nid = nid.trim();
    if (passport.trim()) payload.passport = passport.trim();
    if (dob) payload.date_of_birth = dob;
    if (nationality) payload.nationality = nationality;
    if (phone.trim()) payload.phone = phone.trim();
    if (email.trim()) payload.email = email.trim();
    if (type === "business" && owners.length > 0) {
      payload.beneficial_owners = owners
        .filter((o) => o.full_name.trim().length > 0)
        .map((o) => ({
          full_name: o.full_name.trim(),
          nid: o.nid.trim() || undefined,
          passport: o.passport.trim() || undefined,
          date_of_birth: o.date_of_birth || undefined,
          nationality: o.nationality.trim() || undefined,
          ownership_pct: o.ownership_pct ? Number.parseFloat(o.ownership_pct) : undefined,
        }));
    }

    try {
      const r = await fetch(`/api/customers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "onboarding failed");
      setResult(json as CustomerView);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to onboard customer.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const goToDetail = () => {
    if (result) router.push(`/customers/${result.id}`);
  };

  return (
    <div className="space-y-8">
      <Section eyebrow="Customer profile">
        <form onSubmit={handleSubmit} className="space-y-6 px-6 py-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="External customer ID *">
              <input
                type="text"
                value={externalId}
                onChange={(e) => setExternalId(e.target.value)}
                placeholder="CUST-100345"
                required
                className="mono-input"
              />
            </Field>
            <Field label="Customer type">
              <div className="flex border border-border">
                {(["individual", "business"] as const).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setType(opt)}
                    className={`px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                      type === opt ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </Field>
            <Field label="Full name *">
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} required className="mono-input" />
            </Field>
            <Field label="Date of birth (individuals)">
              <input
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                disabled={type === "business"}
                className="mono-input"
              />
            </Field>
            <Field label="Nationality (ISO code)">
              <input type="text" value={nationality} onChange={(e) => setNationality(e.target.value)} className="mono-input" />
            </Field>
            <Field label="Phone">
              <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className="mono-input" />
            </Field>
            <Field label="Email">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="mono-input" />
            </Field>
            <Field label="NID">
              <input type="text" value={nid} onChange={(e) => setNid(e.target.value)} className="mono-input" />
            </Field>
            <Field label="Passport">
              <input type="text" value={passport} onChange={(e) => setPassport(e.target.value)} className="mono-input" />
            </Field>
            <Field label="City">
              <input type="text" value={city} onChange={(e) => setCity(e.target.value)} className="mono-input" />
            </Field>
            <Field label="Country">
              <input type="text" value={country} onChange={(e) => setCountry(e.target.value)} className="mono-input" />
            </Field>
          </div>

          {type === "business" ? (
            <div className="space-y-4 border-t border-border pt-6">
              <div className="flex items-center justify-between">
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  <span aria-hidden className="mr-2 text-accent">┼</span>
                  Beneficial owners ({owners.length})
                </p>
                <button
                  type="button"
                  onClick={addOwner}
                  className="border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background"
                >
                  Add owner
                </button>
              </div>
              {owners.map((owner, idx) => (
                <div key={idx} className="grid grid-cols-1 gap-3 border border-border p-4 md:grid-cols-3">
                  <Field label={`Owner ${idx + 1} · full name`}>
                    <input
                      type="text"
                      value={owner.full_name}
                      onChange={(e) => updateOwner(idx, { full_name: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <Field label="DOB">
                    <input
                      type="date"
                      value={owner.date_of_birth}
                      onChange={(e) => updateOwner(idx, { date_of_birth: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <Field label="Nationality">
                    <input
                      type="text"
                      value={owner.nationality}
                      onChange={(e) => updateOwner(idx, { nationality: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <Field label="NID">
                    <input
                      type="text"
                      value={owner.nid}
                      onChange={(e) => updateOwner(idx, { nid: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <Field label="Passport">
                    <input
                      type="text"
                      value={owner.passport}
                      onChange={(e) => updateOwner(idx, { passport: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <Field label="Ownership %">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="0.1"
                      value={owner.ownership_pct}
                      onChange={(e) => updateOwner(idx, { ownership_pct: e.target.value })}
                      className="mono-input"
                    />
                  </Field>
                  <button
                    type="button"
                    onClick={() => removeOwner(idx)}
                    className="md:col-span-3 border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-destructive transition hover:bg-destructive hover:text-background"
                  >
                    Remove owner
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          {error ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              <span aria-hidden className="mr-2">┼</span>
              ERROR · {error}
            </p>
          ) : null}

          <div className="flex items-center justify-end gap-3 border-t border-border pt-6">
            <button
              type="submit"
              disabled={submitting}
              className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
            >
              {submitting ? "Onboarding…" : "Onboard + screen"}
            </button>
          </div>
        </form>
      </Section>

      {result ? (
        <Section eyebrow={`Decision · ${result.kyc_status.toUpperCase()}`}>
          <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-3">
            <Tile label="Risk score" value={`${result.risk_score ?? 0}`} tone={riskTone(result.risk_level)} />
            <Tile label="Risk level" value={(result.risk_level || "—").toUpperCase()} tone={riskTone(result.risk_level)} />
            <Tile label="KYC status" value={result.kyc_status.toUpperCase()} tone={statusTone(result.kyc_status)} />
          </div>
          <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
            <button
              type="button"
              onClick={goToDetail}
              className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground"
            >
              View customer
            </button>
          </div>
        </Section>
      ) : null}

      <style jsx>{`
        :global(.mono-input) {
          border: 1px solid hsl(var(--border));
          background: hsl(var(--background));
          padding: 0.5rem 0.75rem;
          font-family: var(--font-mono);
          font-size: 0.875rem;
          color: hsl(var(--foreground));
          width: 100%;
        }
        :global(.mono-input:focus) {
          outline: none;
          border-color: hsl(var(--accent));
        }
        :global(.mono-input:disabled) {
          opacity: 0.5;
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function Tile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex flex-col gap-2 border border-border p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
      <p className={`font-mono text-3xl tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}
