# KESTREL — V3 build prompt (sovereign AI + agentic + on-prem)

**Goal:** Take Kestrel from "world-class AML platform that runs on Claude via OpenRouter" to "national-grade AML platform that runs on a Bangladesh-trained sovereign model with Claude as fallback, supports agentic investigations, and is on-prem deployable for institutions that demand it."

V2 closed 2026-05-05. The 18-capability matrix in `docs/world-class-capability-matrix.md` shows 14 at Excellent, 2 at Partial-with-plan, 0 at Missing. **V3 closes the two Partial-with-plan items** (sovereign AI / on-prem) and adds agentic investigations as a new Excellent.

This prompt is reconciled against `CLAUDE.md` (auto-loaded) and the V2-shipped state. Read in this order before writing any code:

1. `CLAUDE.md` — current project state.
2. `docs/world-class-capability-matrix.md` — V2 closure self-assessment.
3. `KESTREL-WORLD-CLASS-BUILD-V2.md` § "Addendum — sovereign AI track" — the original architecture sketch, still valid.
4. `engine/app/ai/` — every file. The provider abstraction, audit hook, redaction layer, and red-team harness are already in place.
5. `engine/app/services/billing.py` — V3 will add a `sovereign_ai` feature flag here, gated behind enterprise.

Estimated time: **8–10 weeks** of focused work. Months 1-2 build infrastructure; first sovereign model lands in production traffic in month 3 behind a confidence-routing fallback.

---

## STRATEGIC CONTEXT

V2 closed with three durable wins:

- **Buyable**. Three plans in code (Tk 60 lakh / Tk 1.5 crore / Tk 4 crore), feature flags enforced at the route layer with 402 PAYMENT REQUIRED on starter-tier overage.
- **Demoable**. `/demo` public route with three-persona explainer; same data, three views; weekly Beat refresh keeps the dataset current.
- **Operationally credible**. Public status page driven by 5-minute uptime ledger; SLA commitment (99.5% Pro / 99.9% Enterprise); 8 Beat jobs in production.

What V3 unlocks strategically:

1. **The BFIU pitch becomes a closing pitch.** Today: "we use Claude via OpenRouter." Post-V3: "we use a Bangladesh-trained model running in-country, with Claude as fallback for the long tail." That's the difference between BFIU saying "interesting" and BFIU saying "deployable."
2. **The first Tier-3 customer becomes purchasable.** Banks with on-prem mandates (typically the foreign-bank subsidiaries operating under home-jurisdiction policy) can't buy Kestrel today. V3 closes that gap.
3. **Agentic investigations close the last "Missing" capability.** Tookitaki has it; NICE Actimize doesn't. We currently don't. After V3 we do.

Three things V3 deliberately does NOT touch:

- The 18-capability matrix's Excellent items. They are already excellent. Adding features to them is not how V3 increases the surface area.
- The bank-direct sales motion. V2 P2's `/signup/bank` is good and stays as-is.
- Pricing. The plans are right. V3 may add a `sovereign_ai_eligible` feature flag, but the prices don't change.

---

## ARCHITECTURE PRINCIPLES

1. **Sovereign first, Claude fallback.** Every AI surface in V3 routes through a confidence check. If the sovereign model returns high-confidence output, ship it. Otherwise fall back to Claude and *log the fallback as training data*. This is the single most important architectural decision in V3.

2. **Outcome logging is non-negotiable.** Every AI call — pre-V3 already, post-V3 mandatory — writes to `ai_outcome_log` with the prompt (redacted), the output, the provider+model, the analyst correction (if any), and the eventual outcome label. Without this we have nothing to train on.

3. **Quality gates are one-way.** A new sovereign-model adapter ships only when it passes held-out evaluation, the red-team adversarial corpus, and per-task accuracy gates. Promotion is one-way through the gate; degradation triggers automatic rollback.

4. **On-prem is a packaging concern, not a code-path concern.** The same engine + web binary deploys to Render today and to a customer's VPC tomorrow. We package, we don't fork.

5. **Agentic investigations are bounded.** Multi-step agents have a hop budget, a tool whitelist, and a hard wall-clock cap. We do not hand the analyst's seat to an unbounded LLM loop.

---

## PRECONDITIONS — RUN HOUSEKEEPING FIRST

V2 left a small punch list that should be cleared before V3 starts:

1. Set `KESTREL_WATCHLIST_INGESTION_ENABLED=true` on Render. Verify network egress from the engine container to OFAC SDN, UN consolidated, and UK OFSI URLs. Once verified, the daily Beat task starts populating `watchlist_entries` with real upstream data — important because the V3 sovereign model will train on screening calls and the screening calls are noticeably more valuable when the watchlist has real entries.
2. Provision `COMPLYADVANTAGE_API_KEY` on Render. The adverse-media adapter switches stub → live with no code change.
3. Provision the EU FSF watchlist credential (1-day wire-up). Adapter is in place at `engine/app/screening/sources/eu.py`.
4. Regenerate the Render Beat deploy hook URL and update the `RENDER_BEAT_DEPLOY_HOOK_URL` GitHub secret. The current URL returns 404; engine still deploys via Render's connected-repo path, but this should be fixed before V3 lands new Beat jobs.
5. Apply remaining multi-bank seed chunks (64 accounts + 105 transactions + 35 STRs) via `python -m seed.multi_bank_synthetic --apply` from any environment with `DATABASE_URL` set.
6. Install Vercel Marketplace Resend integration on the kestrel project. Verifies `enso-intelligence.com` for transactional email; flips `RESEND_API_KEY` from absent to present so briefing-intake emails actually fire.

Mark each as done before starting V3 Phase 1. Items 1-3 are not blockers but they make the V3 work much more demoable.

---

## BUILD PHASES

Seven phases. The sovereign-AI track (phases 1, 2, 4, 5) runs as a continuous backbone with multi-week gaps between phases for data accumulation; the agentic + on-prem + ops phases (3, 6, 7) run in parallel as separate tracks. Each phase is shippable independently.

---

## PHASE 1 — AI OUTCOME LOGGING (Week 1) ✅ SHIPPED 2026-05-05

Two commits: `157fa73` (engine: migration 019 + dual-write in `record_ai_invocation` + AIOrchestrator timing + correction service + 3 endpoints + 12 tests), pending commit (web dashboard at `/admin/ai-outcomes` + nav).

**Outcome:** every AI call now writes to `ai_outcome_log` with the redacted prompt, structured output, latency, token counts. Dashboard shows per-task correction-rate. Engine routes 123 → 126. pytest 268 → 280.

**Deferred to follow-up (does not block P2):** thread `meta.outcome_log_id` from the AI envelope into existing call sites — STR draft narrative editor (capture diff on edit → POST `/api/ai/outcomes/{id}/correction`), alert explanation panel (capture dismiss as `outcome_label='rejected'`), KYC review (capture override as `outcome_label='edited'`). Infrastructure is in place; the API surface accepts these calls today; UI just needs to fire them.

The detail below stays for reference.

Foundation. Every AI call writes to `ai_outcome_log` so V3 phases 4-5 have a corpus to train on. The existing `engine/app/ai/audit.py::record_ai_invocation` hook is the integration point — extend it, don't fork.

### Task 1.1 — Migration 019: ai_outcome_log

```sql
CREATE TABLE ai_outcome_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid REFERENCES organizations(id),
  task_name text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  prompt_redacted text NOT NULL,
  prompt_digest text NOT NULL,
  output_json jsonb NOT NULL,
  confidence numeric,
  analyst_correction jsonb,
  outcome_label text CHECK (outcome_label IS NULL OR outcome_label IN ('true_positive','false_positive','accepted','rejected','edited')),
  latency_ms integer NOT NULL,
  prompt_tokens integer,
  completion_tokens integer,
  cost_usd numeric,
  fallback_from_provider text,
  fallback_from_model text,
  request_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_outcome_task_created ON ai_outcome_log (task_name, created_at DESC);
CREATE INDEX idx_ai_outcome_org_created ON ai_outcome_log (org_id, created_at DESC);
CREATE INDEX idx_ai_outcome_with_correction
  ON ai_outcome_log (task_name, created_at DESC)
  WHERE analyst_correction IS NOT NULL;

ALTER TABLE ai_outcome_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY ai_outcome_select ON ai_outcome_log
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());
```

### Task 1.2 — Wire `record_ai_invocation` into every AI surface

Audit every call site that invokes a provider adapter today and ensure `record_ai_invocation` is called with the full payload (prompt + output + token counts + latency + request_id correlation). The shape exists; the gap is coverage. Likely call sites:

- `engine/app/ai/routing.py` — task dispatch.
- `engine/app/services/ai_*` — STR narrative, alert explanation, executive briefing, typology suggestion, entity extraction.
- `engine/app/services/realtime_scoring.py` — when AI explanations get added (currently rule-based; sovereign AI track adds an explanation pass).

Test every wiring: `record_ai_invocation` should write exactly one row per provider call, and the row should include the `request_id` so end-to-end correlation works.

### Task 1.3 — Analyst correction capture

The most valuable training signal is "the AI was wrong, here's the right answer." Wire correction capture into:

- STR narrative: when a CAMLCO edits the AI-drafted narrative on a draft STR, diff old vs new and write the diff to `analyst_correction`.
- Alert explanation: when an analyst dismisses an AI-generated explanation as wrong, capture the dismissal as a `false_positive` outcome.
- KYC review: when a CAMLCO overrides the AI-suggested decision (e.g. flips a recommended `review` to `approved`), capture the override.

Each correction becomes a training pair. Ship a `services/ai_outcome.py` helper that any UI surface can call.

### Task 1.4 — Outcome dashboard

New page `web/src/app/(platform)/admin/ai-outcomes/page.tsx`. Shows per-task accuracy proxy (correction rate), provider distribution, average latency, and the top 50 most-recently-corrected entries. Regulator + admin only. Used to decide when there's enough data to start training.

**Estimate: 1 week.**

---

## PHASE 2 — CONFIDENCE ROUTING (Week 2) ✅ SHIPPED 2026-05-05

One commit (engine-only; no web changes). New modules: `engine/app/ai/thresholds.py` (per-task confidence + rollout %), `engine/app/ai/confidence.py` (`compute_schema_validity` + `cap_confidence`). `ProviderName.SOVEREIGN` reserved enum. Settings: `ai_sovereign_url`, `ai_sovereign_api_key`, `ai_sovereign_model`, `ai_sovereign_threshold_default`. `resolve_task_routes` prepends sovereign at index 0 when `_sovereign_configured` AND `is_sovereign_eligible`. `AIOrchestrator.invoke` checks `confidence >= threshold_for(task)` and falls through (logging the fallback signal to `ai_outcome_log`) when below; bottom-of-chain always accepted. `HeuristicProvider` returns its own confidence capped at 0.5.

**No behavior change today** — `MIN_CONFIDENCE_TO_ACCEPT = 1.01` everywhere + `TASK_ROLLOUT_PCT = 0` everywhere = sovereign is never tried, every existing call routes through OpenAI/Anthropic exactly as before. Flipping a single per-task value in `app/ai/thresholds.py` is the V3 P5 unlock.

17 new tests; pytest 280 → 297. Engine routes unchanged at 126.

The detail below stays for reference.

Scaffold the "sovereign first, Claude fallback" routing in `engine/app/ai/routing.py`. The pattern goes in *now*, even though the sovereign side is empty — when Phase 4 lands the first sovereign adapter, it just slots in.

### Task 2.1 — Routing rewrite

```python
async def route_ai_task(task: str, prompt: str, *, request_id: str) -> AIResponse:
    sovereign = providers.sovereign_for(task)
    if sovereign is not None:
        sovereign_response = await sovereign.invoke(prompt)
        if sovereign_response.confidence >= settings.AI_SOVEREIGN_THRESHOLD:
            await record_ai_invocation(..., provider=sovereign.name, ...)
            return sovereign_response
        # Fall through to fallback. Log the fallback as a training signal.
        await record_ai_invocation(
            ...,
            provider=sovereign.name,
            confidence=sovereign_response.confidence,
            outcome_label="rejected",  # rejected by the threshold
        )

    fallback = providers.fallback_for(task)
    fallback_response = await fallback.invoke(prompt)
    await record_ai_invocation(
        ...,
        provider=fallback.name,
        fallback_from_provider=sovereign.name if sovereign else None,
    )
    return fallback_response
```

Ship with `AI_SOVEREIGN_THRESHOLD = 1.01` so every call still routes to Claude. The pattern is in place; the conditional just doesn't fire yet. Sets up Phase 4-5 to flip the threshold without a structural rewrite.

### Task 2.2 — Confidence sources for the heuristic provider

The existing `HeuristicProvider` (used as a degraded-mode fallback when no real AI is configured) returns no confidence today. Add one — schema-validity score (1.0 if the output validates against the expected JSON schema, 0.0 if it doesn't, partial otherwise). This is the "if the output is valid against the expected JSON schema and the structured fields look populated, ship it" rule from the V2 sovereign-AI addendum.

### Task 2.3 — Per-task threshold registry

`engine/app/ai/thresholds.py` maps task name → threshold:

```python
TASK_THRESHOLDS: dict[str, float] = {
    "alert_explanation": 0.75,
    "str_narrative": 0.85,        # higher bar — narrative ships into a regulatory filing
    "entity_extraction": 0.90,    # very high bar — false positives contaminate the shared pool
    "executive_briefing": 0.70,
    "typology_suggestion": 0.65,
}
```

**Estimate: 1 week.**

---

## PHASE 3 — AGENTIC AI INVESTIGATIONS (Weeks 3-4) ✅ SHIPPED 2026-05-05

Two commits: `aa4c932` (engine: agent loop primitive + 6-tool registry + service + 3-route router + migration 020 + 5 red-team scenarios + 21 tests) and pending (web: investigation panel on entity dossier + 2 API proxies + promote-to-STR sessionStorage hand-off).

**Outcome:** capability matrix flips "Agentic AI investigations" from Partial → Excellent. Net **15/18 at Excellent**. Engine routes 126 → 129. pytest 297 → 319.

**Deferred follow-ups (do not block P4):**
- Replace the deterministic heuristic decider with the AI-orchestrator-driven hop decider (calls `INVESTIGATION_AGENT_HOP` task per hop). Drop-in replacement; orchestrator already handles the threshold gate + outcome logging.
- SSE streaming of hop progress to the web UI (V1 ships synchronous POST + spinner — ~3-5s wall-clock per investigation under the heuristic decider).
- Full STR-prefill integration when promoting an investigation to a draft STR. Currently sessionStorage stows the evidence + the URL carries the investigation id; the STR draft form ignores it for now.

The detail below stays for reference.

Closes the last Missing capability. Multi-step investigation agent that pulls related entities, drafts hypotheses, surfaces evidence, and produces an investigation summary the analyst can promote to an STR.

### Task 3.1 — Agent loop primitive

`engine/app/agents/investigation_agent.py`. Bounded execution: max 8 hops, hard 60-second wall-clock cap, tool whitelist (resolve_entity, neighbours, recent_alerts, recent_strs, screen_entity, build_narrative). The agent returns:

```json
{
  "hypothesis": "...",
  "evidence": [{"tool": "neighbours", "args": {...}, "result": {...}}],
  "suggested_actions": ["draft_str", "open_case", "request_str_supplement"],
  "confidence": 0.72,
  "hops_used": 5,
  "latency_ms": 22340
}
```

### Task 3.2 — `POST /agents/investigate`

Engine route. Takes `{entity_id, prompt}`. Returns the agent output and persists to a new `agent_investigations` table (migration 020).

### Task 3.3 — Investigation panel on entity dossier

New section on `/investigate/entity/[id]`: "Investigate this entity (AI)" button. Streams the agent's hops as they execute (Server-Sent Events), shows the final hypothesis + evidence + suggested actions. Promote-to-STR button drafts a narrative pre-populated with the investigation evidence.

### Task 3.4 — Red-team corpus expansion

Extend `engine/app/ai/redteam/corpus.py` with agent-specific adversarial scenarios: prompt injection through entity metadata, tool-output poisoning (an entity whose `display_name` contains an instruction), hop-budget exhaustion. Promotion gates a new agent adapter only if it survives the corpus.

**Estimate: 2 weeks.**

---

## PHASE 4 — SOVEREIGN MODEL TRAINING PIPELINE (Weeks 5-6) ✅ FRAMEWORK SHIPPED 2026-05-05

One commit (`9c3b146`, engine + infra). Framework-shipped, training-cycle-deferred:

- `engine/scripts/export_training_corpus.py` — real CLI, deterministic dedup + JSONL output, optional Supabase Storage upload.
- `infra/training/lora_finetune.py` — Modal-flavored scaffold with real corpus loading + train/eval split + supported base model whitelist. Training step itself is a documented `NotImplementedError` stub (the actual transformers + peft Trainer block is a comment ready to swap in).
- `engine/scripts/generate_synthetic_corpus.py` — uses the existing `AIOrchestrator` (Claude) to generate training pairs across all 6 AI tasks; written to a separate file so quality gates can A/B corrections-only vs corrections+synthetic.
- `engine/app/ai/providers/sovereign_adapter.py` — full `LLMProvider` implementation against a vLLM-compatible HTTP endpoint. Token-log-prob → confidence conversion. Registered in the orchestrator's default providers dict; routing only selects it once `AI_SOVEREIGN_URL` is set + a per-task rollout > 0.

30 new tests; pytest 319 → 349. No new endpoints; no new migrations.

**The first real cycle waits for the corpus.** ~30–60 days of analyst corrections in `ai_outcome_log` is the realistic threshold. Until then the framework sits ready; ops triggers it from `infra/training/lora_finetune.py` when the corpus is meaningful.

The detail below stays for reference.

Build the pipeline. First fine-tune cycle in Week 6. Quality gate evaluation in Week 7 (Phase 5).

### Task 4.1 — Training data export

`engine/scripts/export_training_corpus.py`. Pulls from `ai_outcome_log` over the last 60 days where `analyst_correction IS NOT NULL`. Format: JSONL with `{prompt, expected_output, task_name}`. Deduplicates on `prompt_digest`. Writes to `kestrel-exports` Storage bucket as `training/v3-month-N/corpus.jsonl`.

### Task 4.2 — LoRA fine-tune harness

`infra/training/lora_finetune.py`. Runs on Modal or RunPod (operator's choice — pick one and stick with it). Inputs: base model (Llama 3.3 70B or Qwen 2.5 72B), training corpus, validation split, 4-8 hour budget, A100 or H100. Outputs: a LoRA adapter file + a metrics JSON.

### Task 4.3 — Synthetic data augmentation

The `analyst_correction`-only corpus will be small at first. Augment with Claude-generated synthetic data covering the task surface. Keep this pipeline separate from the live-correction pipeline so quality gates can compare adapters trained on `corrections only` vs `corrections + synthetic`.

### Task 4.4 — Sovereign provider adapter

`engine/app/ai/providers/sovereign_adapter.py`. HTTP client to a self-hosted inference endpoint (vLLM behind Modal or a dedicated GPU box). Returns `AIResponse` with token-level log-probs as the confidence source. Slots into the routing pattern from Phase 2 with no structural change.

**Estimate: 2 weeks.**

---

## PHASE 5 — QUALITY GATES + GRADUAL ROLLOUT (Week 7)

A new sovereign adapter ships only after passing:

1. **Held-out evaluation set**: scores within 5% of Claude on the same prompts (precision, recall, structured-output validity per task). If significantly worse, don't promote — keep training.
2. **Red-team adversarial set**: doesn't hallucinate on the existing red-team corpus + the agent-specific scenarios from Phase 3.4.
3. **Business-critical task accuracy gates** (per task):
   - STR drafts must include all required regulatory fields (subject, narrative, channel, date range, category) — schema-validity is a hard 100%.
   - Entity-extraction precision > 0.9 (false positives in entity resolution contaminate the shared pool).
   - Alert-explanation reasons must reference at least one rule code from the rule hits — no inventing reasons.
   - Executive-briefing outputs must not contain any redacted PII patterns in the output (NID/account/phone regex check).

### Task 5.1 — Promotion harness

`engine/scripts/promote_sovereign_adapter.py`. Runs the three gates against a candidate adapter. Outputs a YAML report with pass/fail per gate. CI gates the adapter promotion on this report being all-pass.

### Task 5.2 — Gradual rollout traffic split

`engine/app/ai/thresholds.py` gains a per-task rollout %:

```python
TASK_ROLLOUT_PCT: dict[str, int] = {
    "alert_explanation": 10,   # 10% of alert_explanation calls go to sovereign
    "str_narrative": 0,        # not yet
}
```

Routing logic flips a coin per call; logs the assignment for outcome comparison.

### Task 5.3 — Rollback automation

A new Beat task `sovereign_health_check` runs every 30 min. Reads the last 1000 sovereign-vs-Claude pairs from `ai_outcome_log`. If sovereign correction rate exceeds Claude's by more than 15% on any task, automatically reduce that task's rollout % by 25%. Page the operator if rollout reaches 0%.

**Estimate: 1 week.**

---

## PHASE 6 — ON-PREM PACKAGING (Weeks 8-10, conditional)

Only fire when a Tier-3 customer signs. Don't build speculatively.

### Task 6.1 — Container packaging

`infra/onprem/`. Multi-stage Dockerfile that bundles engine + worker + beat + web (next.js standalone build) into one image, plus a docker-compose.yml that brings up Postgres + Redis + Caddy. Customer's only requirement is Docker Compose.

### Task 6.2 — Migration runner

A boot-time script that runs `supabase/migrations/*.sql` against the customer's Postgres via a vendored `psql`. Idempotent.

### Task 6.3 — On-prem AI mode

The sovereign adapter from Phase 4 has to also work in air-gapped environments. Customer's GPU box runs vLLM; engine talks to it over LAN. No fallback to Claude (no internet) — degrade to the heuristic provider for fields where sovereign doesn't clear threshold.

### Task 6.4 — Air-gapped watchlist sync

Watchlist sources need a manual-import mode. Operator runs `engine/scripts/import_watchlist_archive.py` against a local file dump of the OFAC / UN / UK OFSI XML; engine ingests offline.

### Task 6.5 — Licensing + telemetry

Customer-side license file with feature flags (mirrors the cloud `plan_id` model). Optional outbound telemetry pingback to Kestrel HQ for billing reconciliation; defaults off in air-gapped mode.

**Estimate: 4–6 weeks. Don't start until a customer signs.**

---

## PHASE 7 — OPERATIONAL MATURITY (1–2 weeks, anytime)

Small wins that pay for themselves. Schedule whenever there's a gap.

### Task 7.1 — Stripe / metered billing

`engine/app/services/billing.py` already defines plans in code. Add a Stripe customer + price-ID mapping per plan. Webhook ingests subscription events. Failed-payment handling: 7-day grace, then plan downgrades to `starter` until paid.

### Task 7.2 — Hard transaction-cap enforcement

Migration 021 adds `metered_writes` (org_id, period_start, transaction_count). Every successful `POST /transactions/score` increments. Plan-cap check returns 402 + upgrade message when monthly cap exceeded.

### Task 7.3 — Audit-log retention policy

`audit_log` accumulates fast. Add a daily Beat task that archives rows older than 365 days to a cold-storage bucket and deletes from Postgres. Compliance retention is satisfied by the cold storage; query latency on the live table stays bounded.

### Task 7.4 — Performance regression CI

Add a CI job that runs `engine/tests/test_realtime_scoring.py::test_scoring_latency` (new, this task) against a 100-call synthetic burst and fails the build if p99 > 500ms. Catches regressions before they hit prod.

**Estimate: 1–2 weeks across the four sub-tasks.**

---

## WHAT NOT TO TOUCH

The V2-shipped surfaces are stable. Don't refactor them in V3:

- The 18-capability matrix's Excellent items. Don't add features to them.
- The bank-direct landing at `/banks` and the signup flow at `/signup/bank`. The pricing tiers don't change.
- The Sovereign Ledger design system. New V3 surfaces follow the existing `Section` / `Eyebrow` / `Field` patterns. Don't introduce a parallel design language.
- The plan definitions in code (`services/billing.py`). Adding a `sovereign_ai` feature flag is fine; changing prices isn't.
- The 18 migrations. Only add new ones (019+).
- The 8 Beat jobs. Extend (add new scheduled tasks); never modify or remove existing ones.
- The 123 existing API routes. Extend, never remove or modify behavior.

If a change in V3 accidentally touches a V2-shipped artifact, stop and revert.

---

## DEMO FLOWS

### Sovereign-AI demo (BFIU procurement, post-Phase 5)

1. Land on `/overview` as BFIU Director.
2. Open any alert → AI explanation panel shows.
3. Inspect the request_id in the panel; query `ai_outcome_log` and show the `provider` field.
4. Show: 30% of explanations now come from `kestrel-sovereign-v1` (Bangladesh-trained), 70% from Claude.
5. Show the held-out eval report: sovereign within 3% of Claude on alert_explanation.
6. Closing line: "Bangladesh-trained, hosted in-country, falls back to Claude only when confidence is low. Same engine, same quality gates, sovereign by default within 6 months."

### Agentic investigation demo (post-Phase 3)

1. Open entity dossier on a flagged subject.
2. Click "Investigate this entity (AI)". Watch the hops stream in.
3. Agent surfaces three connected entities, two stale STRs, one new typology hit.
4. Agent recommends: draft STR + open case.
5. Click promote → new draft STR is pre-populated with the investigation narrative.
6. CAMLCO edits (if needed) and submits.
7. The edit is captured in `ai_outcome_log` as an `analyst_correction` and feeds the next training cycle.

### On-prem demo (post-Phase 6, conditional)

1. Power on the customer's appliance.
2. Browser to `https://kestrel.local`.
3. Show: same UI, same data flow, no internet egress.
4. Inspect the AI panel: sovereign adapter answering; no Claude fallback because no network.
5. Watchlist imported manually via the air-gapped sync script; entries visible.
6. Closing line: "Same product. No internet required. Foreign-bank subsidiaries operating under home-jurisdiction policy can deploy this."

---

## BUILD ORDER WITH WEEKS

| Week | Phase | Tasks | Verification |
|---|---|---|---|
| 1 | P1 outcome logging | 1.1, 1.2, 1.3, 1.4 | Migration 019 applied; every AI call writes to `ai_outcome_log`; correction capture wired into STR + alert + KYC; admin dashboard live. |
| 2 | P2 confidence routing | 2.1, 2.2, 2.3 | Routing rewritten with sovereign-first pattern (threshold = ∞); heuristic provider returns confidence; per-task thresholds exist. Every existing AI call still routes to Claude — pattern is in place. |
| 3-4 | P3 agentic investigations | 3.1, 3.2, 3.3, 3.4 | `POST /agents/investigate` live; entity dossier has the investigation panel; red-team corpus expanded; promote-to-STR works end-to-end. |
| 5-6 | P4 training pipeline | 4.1, 4.2, 4.3, 4.4 | Training corpus exporting weekly; first LoRA cycle complete; sovereign adapter implemented; not yet promoted. |
| 7 | P5 quality gates + rollout | 5.1, 5.2, 5.3 | Promotion harness all-pass on candidate adapter; first task at 10% rollout; rollback automation live. |
| 8+ | P6 on-prem | 6.1-6.5 | Conditional on customer signing. |
| Anytime | P7 ops maturity | 7.1, 7.2, 7.3, 7.4 | Stripe wired; hard caps enforced; audit-log retention live; latency regression CI catching p99 > 500ms. |

Each phase ends with a live-verification commit message: `PHASE X COMPLETE — [verification details]`. Push every task as its own feature branch when there are external eyes; direct-to-main remains fine pre-pilot.

---

## ONE NON-NEGOTIABLE

**Quality gates are one-way.** A new sovereign adapter ships only after passing held-out eval + red-team + per-task accuracy gates. Promotion through the gates is automated; degradation triggers automatic rollback via `sovereign_health_check`. No human "let's just see what happens" promotions. The point of training a sovereign model is to win on capability; if a candidate model is worse than Claude, we don't ship it just because it's ours.

This is the single behavior that protects the customer through the V3 transition. Don't relax it.

---

## SUCCESS CRITERIA

When V3 closes:

| Capability | Pre-V3 | Post-V3 |
|---|---|---|
| Real-time transaction monitoring | ✅ EXCELLENT | ✅ EXCELLENT (sovereign explanations on every alert) |
| AI-powered alert generation | ✅ EXCELLENT | ✅ EXCELLENT (10-50% sovereign by default) |
| False-positive reduction | ⚠️ PARTIAL | ✅ EXCELLENT (ML loop live, training on corrections) |
| Sanctions / PEP / adverse media screening | ✅ EXCELLENT | ✅ EXCELLENT |
| KYC / CDD automation | ✅ EXCELLENT | ✅ EXCELLENT |
| Agentic AI investigations | ⚠️ PARTIAL | ✅ EXCELLENT |
| On-prem flexibility | ⚠️ PARTIAL | ✅ EXCELLENT (first deployment shipped) |
| Sovereign AI (V3-introduced capability) | — | ✅ EXCELLENT (production traffic on Bangladesh-trained model) |

**Net: 14/18 → 18/18 at Excellent** (where applicable; on-prem and sovereign AI are conditional on first deployments).

After V3:

- The sovereign-AI track is live in production, with a continuously-improving training loop.
- Agentic investigations close the last "Missing" capability.
- On-prem packaging is real and demoable to home-jurisdiction-bound institutions.
- Stripe, hard cap enforcement, audit retention, and latency CI bring operational maturity to first-pilot quality.

After V3, the BFIU pitch becomes: "We are the national AML platform. Bangladesh-trained AI, hosted in-country, deployable on your infrastructure, demoable to any bank in 30 minutes."

After V3, Kestrel competes globally on capability and wins regionally on positioning.

---

## CONTINUITY

When the next session picks this up, drop the resume snippet:

> "Read `KESTREL-V3-PROMPT.md`. Pick up Phase N task M. Same workflow as V2: engine commit → migrations applied via Supabase MCP → web/docs commit → live-verify on prod → memory update."

Same chunking pattern as V2: one big engine commit per phase + one smaller web/docs commit. Same direct-to-main rule pre-pilot. Same migration numbering (start from 019). Same Sovereign Ledger UI conventions. Same 402 enforcement on starter-tier callers (sovereign AI surfaces sit behind the existing `realtime` / `sanctions` / `kyc` features for now; a new `sovereign_ai` feature flag can gate the agentic investigation surface in Phase 3.2 if you want it to be enterprise-only).

The V3 work is technically more sophisticated than V2 but operationally smaller — fewer phases, fewer surfaces, more depth per surface. The pattern that worked for V2 (small, well-tested chunks with frequent prod verification) keeps working.

Start when ready.
