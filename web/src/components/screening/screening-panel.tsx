"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import type { Viewer } from "@/types/domain";

const LIST_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "ALL", value: "" },
  { label: "OFAC", value: "OFAC" },
  { label: "UN", value: "UN" },
  { label: "UK OFSI", value: "UK_OFSI" },
  { label: "EU", value: "EU" },
  { label: "BB DOMESTIC", value: "BB_DOMESTIC" },
  { label: "PEP", value: "PEP" },
];

const SOURCE_TONE: Record<string, string> = {
  OFAC: "text-accent",
  UN: "text-foreground",
  UK_OFSI: "text-foreground",
  EU: "text-foreground",
  BB_DOMESTIC: "text-accent",
  PEP: "text-muted-foreground",
  ADVERSE_MEDIA: "text-muted-foreground",
};

interface ScreeningMatch {
  list_source: string;
  list_version: string;
  entry_id: string;
  entry_type: string;
  matched_name: string;
  matched_aliases: string[];
  matched_entry: Record<string, unknown>;
  match_score: number;
  match_reasons: string[];
}

interface ScreeningResponse {
  matches: ScreeningMatch[];
  screened_at: string;
  request_id: string;
}

interface WatchlistRow {
  id: string;
  list_source: string;
  list_version: string;
  entry_type: string;
  primary_name: string;
  aliases: string[];
  date_of_birth: string | null;
  nationality: string | null;
  reason: string | null;
  ingested_at: string | null;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {children}
    </p>
  );
}

function Section({ eyebrow, children }: { eyebrow: string; children: React.ReactNode }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <Eyebrow>{eyebrow}</Eyebrow>
      </div>
      {children}
    </section>
  );
}

function scoreTone(score: number): string {
  if (score >= 0.9) return "text-destructive";
  if (score >= 0.75) return "text-accent";
  return "text-foreground";
}

export function ScreeningPanel({ viewer }: { viewer: Viewer }) {
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [nationality, setNationality] = useState("");
  const [nid, setNid] = useState("");
  const [passport, setPassport] = useState("");
  const [minScore, setMinScore] = useState(0.7);
  const [listFilter, setListFilter] = useState("");

  const [response, setResponse] = useState<ScreeningResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [poolPreview, setPoolPreview] = useState<WatchlistRow[]>([]);
  const [poolLoading, setPoolLoading] = useState(true);

  const isRegulator = viewer.persona === "bfiu_director" || viewer.persona === "bfiu_analyst";

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/screening/entries?limit=20`, { cache: "no-store" })
      .then(async (r) => {
        const json = await r.json();
        if (!r.ok) throw new Error(json.detail ?? "watchlist preview");
        if (!cancelled) setPoolPreview((json.rows ?? []) as WatchlistRow[]);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          // Watchlist preview is optional; surface in console only.
          console.warn("watchlist preview failed", err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setPoolLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Candidate name is required.");
      return;
    }
    setLoading(true);
    setError(null);

    const payload: Record<string, unknown> = {
      name: name.trim(),
      minimum_match_score: minScore,
    };
    if (dob) payload.date_of_birth = dob;
    if (nationality) payload.nationality = nationality;
    if (nid) payload.nid = nid;
    if (passport) payload.passport = passport;
    if (listFilter) payload.screening_lists = [listFilter];

    try {
      const r = await fetch(`/api/screening/entity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "screening failed");
      setResponse(json as ScreeningResponse);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to run screening.";
      setError(message);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <Section eyebrow="Candidate · enter the party you want to screen">
        <form className="space-y-6 px-6 py-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Candidate name *
              </span>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Mohammad Karim"
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                required
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Date of birth (optional)
              </span>
              <input
                type="date"
                value={dob}
                onChange={(event) => setDob(event.target.value)}
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Nationality (ISO code)
              </span>
              <input
                type="text"
                value={nationality}
                onChange={(event) => setNationality(event.target.value)}
                placeholder="BD"
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                NID (national ID)
              </span>
              <input
                type="text"
                value={nid}
                onChange={(event) => setNid(event.target.value)}
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Passport
              </span>
              <input
                type="text"
                value={passport}
                onChange={(event) => setPassport(event.target.value)}
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Minimum match score (0–1)
              </span>
              <input
                type="number"
                step="0.05"
                min={0}
                max={1}
                value={minScore}
                onChange={(event) => setMinScore(Number.parseFloat(event.target.value || "0.7"))}
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              List filter
            </span>
            <div className="flex flex-wrap border border-border">
              {LIST_OPTIONS.map((opt) => (
                <button
                  key={opt.value || "all"}
                  type="button"
                  onClick={() => setListFilter(opt.value)}
                  className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    listFilter === opt.value
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="ml-auto border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
            >
              {loading ? "Screening…" : "Run screen"}
            </button>
          </div>
        </form>
      </Section>

      {loading ? (
        <LoadingState label="Resolving watchlist matches" />
      ) : error ? (
        <ErrorState title="Screening failed" description={error} />
      ) : response === null ? (
        <Section eyebrow="Watchlist preview · most recent ingestions">
          {poolLoading ? (
            <LoadingState label="Loading watchlist preview" />
          ) : poolPreview.length === 0 ? (
            <EmptyState
              title="No watchlist entries available"
              description="The watchlist pool is empty. Apply the synthetic seed (engine/seed/load_watchlist_synthetic.py --apply) or wait for the daily ingestion task to land entries."
            />
          ) : (
            <ul className="divide-y divide-border">
              {poolPreview.map((row) => (
                <li key={row.id} className="grid grid-cols-12 items-center gap-4 px-6 py-3">
                  <div className={`col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] ${SOURCE_TONE[row.list_source] ?? "text-foreground"}`}>
                    {row.list_source}
                  </div>
                  <div className="col-span-5 font-mono text-sm text-foreground">
                    {row.primary_name}
                    {row.aliases.length > 0 ? (
                      <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        aka {row.aliases.slice(0, 2).join(" · ")}
                        {row.aliases.length > 2 ? " · …" : ""}
                      </span>
                    ) : null}
                  </div>
                  <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {row.entry_type}
                  </div>
                  <div className="col-span-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground truncate">
                    {row.reason ?? "—"}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      ) : response.matches.length === 0 ? (
        <EmptyState
          title="No matches above threshold"
          description={`Candidate '${name}' did not match any watchlist entry above ${minScore.toFixed(2)}. Lower the threshold or supply more identifiers (DOB, nationality, NID, passport) to widen the search.`}
        />
      ) : (
        <Section eyebrow={`Matches · ${response.matches.length} above threshold`}>
          <ul className="divide-y divide-border">
            {response.matches.map((match) => (
              <li key={match.entry_id} className="grid grid-cols-12 items-start gap-4 px-6 py-4">
                <div className={`col-span-1 font-mono text-[11px] uppercase tracking-[0.22em] ${SOURCE_TONE[match.list_source] ?? "text-foreground"}`}>
                  {match.list_source}
                </div>
                <div className={`col-span-1 text-right font-mono text-lg tabular-nums ${scoreTone(match.match_score)}`}>
                  {match.match_score.toFixed(2)}
                </div>
                <div className="col-span-6 flex flex-col gap-1">
                  <p className="font-mono text-sm text-foreground">{match.matched_name}</p>
                  {match.matched_aliases.length > 0 ? (
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                      aka {match.matched_aliases.slice(0, 4).join(" · ")}
                      {match.matched_aliases.length > 4 ? " · …" : ""}
                    </p>
                  ) : null}
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {match.entry_type}
                    {match.matched_entry.date_of_birth ? ` · DOB ${match.matched_entry.date_of_birth as string}` : ""}
                    {match.matched_entry.nationality ? ` · ${match.matched_entry.nationality as string}` : ""}
                  </p>
                </div>
                <div className="col-span-4 flex flex-col gap-1">
                  {match.match_reasons.map((reason, idx) => (
                    <p key={idx} className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      ┼ {reason}
                    </p>
                  ))}
                  {match.matched_entry.reason ? (
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                      {match.matched_entry.reason as string}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        ┼ {isRegulator ? "Regulator view" : "Bank view"} · screening calls are audit-logged with action=&quot;screening.entity&quot; and a request_id correlator.
        Real-time scoring (POST /transactions/score) screens both parties inline; a hit at score ≥ 0.7 forces hold/reject.
      </p>
    </div>
  );
}
