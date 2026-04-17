"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

type Tab = "account" | "person" | "business";

type Identifier = { entityType: string; value: string; displayName?: string };

type Response = {
  primary_entity_id: string;
  resolved: { id: string; entity_type: string; display_value: string; display_name?: string | null; created: boolean }[];
  connections_created: number;
};

export function NewSubjectForm() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("account");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Account tab fields
  const [account, setAccount] = useState("");
  const [accountName, setAccountName] = useState("");
  const [accountBank, setAccountBank] = useState("");
  const [accountPhone, setAccountPhone] = useState("");
  const [accountNid, setAccountNid] = useState("");

  // Person tab fields
  const [personName, setPersonName] = useState("");
  const [personNid, setPersonNid] = useState("");
  const [personPhone, setPersonPhone] = useState("");
  const [personWallet, setPersonWallet] = useState("");
  const [personAliases, setPersonAliases] = useState("");

  // Entity tab fields
  const [businessName, setBusinessName] = useState("");
  const [businessRegistration, setBusinessRegistration] = useState("");
  const [businessIndustry, setBusinessIndustry] = useState("");
  const [businessPhone, setBusinessPhone] = useState("");
  const [businessUbo, setBusinessUbo] = useState("");

  function buildIdentifiers(): { primary: Tab; list: Identifier[] } {
    const list: Identifier[] = [];
    if (tab === "account") {
      if (account.trim()) list.push({ entityType: "account", value: account.trim(), displayName: accountName || undefined });
      if (accountPhone.trim()) list.push({ entityType: "phone", value: accountPhone.trim() });
      if (accountNid.trim()) list.push({ entityType: "nid", value: accountNid.trim() });
      if (accountName.trim() && accountBank.trim()) {
        list.push({ entityType: "business", value: accountName.trim(), displayName: accountName });
      }
    } else if (tab === "person") {
      if (personName.trim()) list.push({ entityType: "person", value: personName.trim(), displayName: personName });
      if (personNid.trim()) list.push({ entityType: "nid", value: personNid.trim() });
      if (personPhone.trim()) list.push({ entityType: "phone", value: personPhone.trim() });
      if (personWallet.trim()) list.push({ entityType: "wallet", value: personWallet.trim() });
      if (personAliases.trim()) {
        for (const alias of personAliases.split(",")) {
          const trimmed = alias.trim();
          if (trimmed) list.push({ entityType: "person", value: trimmed, displayName: trimmed });
        }
      }
    } else {
      if (businessName.trim()) list.push({ entityType: "business", value: businessName.trim(), displayName: businessName });
      if (businessRegistration.trim()) list.push({ entityType: "nid", value: businessRegistration.trim() });
      if (businessPhone.trim()) list.push({ entityType: "phone", value: businessPhone.trim() });
      if (businessUbo.trim()) list.push({ entityType: "person", value: businessUbo.trim(), displayName: businessUbo });
    }
    return { primary: tab, list };
  }

  async function submit() {
    const { primary, list } = buildIdentifiers();
    if (list.length === 0) {
      setError("Fill in at least the required identifier for this tab.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/intelligence/entities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          primaryKind: primary,
          identifiers: list,
          metadata: { source: "new_subject_form", industry: businessIndustry || undefined },
        }),
      });
      const result = (await readResponsePayload<Response>(response)) as Response | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to create subject."));
        return;
      }
      const successful = result as Response;
      router.push(`/investigate/entity/${successful.primary_entity_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create subject.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create a new subject</CardTitle>
        <CardDescription>
          Pick what you&apos;re entering. Every additional identifier you provide is resolved + linked with same_owner
          connections so the network graph picks up the relationship immediately.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(["account", "person", "business"] as Tab[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                tab === value
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border text-muted-foreground hover:border-primary/40"
              }`}
            >
              {value === "account" ? "Account" : value === "person" ? "Person" : "Entity"}
            </button>
          ))}
        </div>

        {tab === "account" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="Account number (required)">
              <Input value={account} onChange={(event) => setAccount(event.target.value)} placeholder="1781430000701" />
            </Field>
            <Field label="Account name">
              <Input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="RIZWANA ENTERPRISE" />
            </Field>
            <Field label="Bank code">
              <Input value={accountBank} onChange={(event) => setAccountBank(event.target.value)} placeholder="DBBL" />
            </Field>
            <Field label="Phone">
              <Input value={accountPhone} onChange={(event) => setAccountPhone(event.target.value)} placeholder="+88017XXXXXXXX" />
            </Field>
            <Field label="National ID">
              <Input value={accountNid} onChange={(event) => setAccountNid(event.target.value)} placeholder="1234567890123" />
            </Field>
          </div>
        ) : null}

        {tab === "person" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="Full name (required)">
              <Input value={personName} onChange={(event) => setPersonName(event.target.value)} placeholder="Rizwana Ahmed" />
            </Field>
            <Field label="National ID">
              <Input value={personNid} onChange={(event) => setPersonNid(event.target.value)} placeholder="1234567890123" />
            </Field>
            <Field label="Phone">
              <Input value={personPhone} onChange={(event) => setPersonPhone(event.target.value)} placeholder="+88017XXXXXXXX" />
            </Field>
            <Field label="MFS wallet">
              <Input value={personWallet} onChange={(event) => setPersonWallet(event.target.value)} placeholder="01XXXXXXXXX" />
            </Field>
            <Field label="Known aliases (comma-separated)">
              <Textarea value={personAliases} onChange={(event) => setPersonAliases(event.target.value)} rows={2} />
            </Field>
          </div>
        ) : null}

        {tab === "business" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="Business name (required)">
              <Input value={businessName} onChange={(event) => setBusinessName(event.target.value)} placeholder="Rizwana Enterprise Ltd" />
            </Field>
            <Field label="Registration number">
              <Input value={businessRegistration} onChange={(event) => setBusinessRegistration(event.target.value)} placeholder="RJSC-2021-000123" />
            </Field>
            <Field label="Industry">
              <Input value={businessIndustry} onChange={(event) => setBusinessIndustry(event.target.value)} placeholder="Retail trade" />
            </Field>
            <Field label="Primary phone">
              <Input value={businessPhone} onChange={(event) => setBusinessPhone(event.target.value)} placeholder="+88029XXXXXXX" />
            </Field>
            <Field label="Ultimate beneficial owner">
              <Input value={businessUbo} onChange={(event) => setBusinessUbo(event.target.value)} placeholder="Rizwana Ahmed" />
            </Field>
          </div>
        ) : null}

        {error ? <p className="text-sm text-red-300">{error}</p> : null}

        <div className="flex justify-end">
          <Button type="button" disabled={submitting} onClick={() => void submit()}>
            {submitting ? "Creating…" : "Create subject"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
