# Kestrel API integration guide

**Audience:** core-banking integration teams wiring their transaction-processing pipeline to Kestrel for real-time decisioning. **Last updated:** 2026-05-05 (V2 phase 3 / live on `https://kestrel-engine.onrender.com`).

This guide covers the production endpoints under `/transactions/score`. For a procurement-grade overview of cross-bank intelligence, see `docs/cross-bank-intelligence.md`. For tenant-isolation guarantees, see `docs/multi-tenant-isolation-verified.md`.

---

## 1. Base URL & auth

| Environment | Base URL |
|---|---|
| Production | `https://kestrel-engine.onrender.com` |

Every request must carry a Supabase JWT in the `Authorization: Bearer <token>` header. Two issuance paths:

1. **Interactive (CAMLCO + analyst)** — sign in via `https://kestrel-nine.vercel.app/login`; the Supabase session token works directly against the engine.
2. **Service-to-service (core-banking integration)** — provision a service-role API user under your tenant via Admin → API Keys (`/admin/api-keys`). The issued token rotates on a schedule defined by your tier. Treat the token as a secret: never log it, never embed it in client-side code.

Tokens are signed HS256 with `SUPABASE_JWT_SECRET`. The engine validates expiry, issuer, and the `org_id` / `org_type` / `role` / `persona` claims before any request lands at a service. A bank-tenant token cannot read or write another tenant's data — RLS enforces this at the Postgres layer behind the engine.

---

## 2. Real-time transaction scoring

```
POST /transactions/score
```

Score one transaction. Returns a decision and an explainable list of contributing reasons. **Latency target: p50 < 200 ms / p99 < 500 ms.** The endpoint is read-only against the shared intelligence pool (entities + matches) and does not mutate transaction-table state — score, log, audit. Nothing else.

### Request

```json
{
  "transaction_id": "BNK-TXN-000123456",
  "from_account": "1234567890123",
  "to_account": "9876543210987",
  "amount": 1750000,
  "currency": "BDT",
  "channel": "NPSB",
  "transaction_type": "debit",
  "from_account_metadata": {
    "name": "Mohammad Karim",
    "phone": "+880 1711-555-001",
    "nid": "1234567890123",
    "account_open_date": "2026-04-15"
  },
  "to_account_metadata": {
    "name": "Receiver Name",
    "phone": "+880 1700-000-000"
  },
  "timestamp": "2026-05-05T08:30:00+06:00"
}
```

| Field | Required | Notes |
|---|---|---|
| `transaction_id` | yes | Your bank's own transaction ID (echoed back in audit + dashboard). Max 128 chars. |
| `from_account` / `to_account` | yes | Plain account numbers — Kestrel canonicalises (strips separators, uppercases) before lookup. Max 128 chars each. |
| `amount` | yes | Numeric, BDT-denominated by default. |
| `currency` | no | Defaults to `BDT`. Other currencies pass through unchanged for now. |
| `channel` | yes | Allowlist: `NPSB`, `BEFTN`, `RTGS`, `MFS_BKASH`, `MFS_NAGAD`, `MFS_ROCKET`, `CASH`, `CHEQUE`, `CARD`, `WIRE`, `LC`, `DRAFT`. Case-insensitive. |
| `transaction_type` | yes | `credit` or `debit`. |
| `from_account_metadata` / `to_account_metadata` | no | Free-form. The scorer reads `account_open_date` (or `opened_at`) to assess account age. ISO date / datetime. |
| `timestamp` | no | ISO 8601. Defaults to server `now()` if omitted. |

### Response

```json
{
  "log_id": "6997af82-8513-436f-8ffe-2c921afeecab",
  "score": 65,
  "decision": "hold",
  "confidence": 0.78,
  "reasons": [
    {
      "rule": "amount_large",
      "score": 20,
      "reason_text": "Transaction amount BDT 1,750,000 exceeds 10 lakh.",
      "detail": {"amount": 1750000, "threshold": 1000000}
    },
    {
      "rule": "new_account_high_value",
      "score": 20,
      "reason_text": "Originating account opened 20 days ago is sending BDT 1,750,000.",
      "detail": {"account_age_days": 20, "amount": 1750000}
    },
    {
      "rule": "from_cross_bank_flagged",
      "score": 25,
      "reason_text": "From party is reported by 3 institutions (cross-bank match severity=high, risk_score=80).",
      "detail": {"match_id": "...", "bank_count": 3, "risk_score": 80, "severity": "high"}
    }
  ],
  "evidence": {
    "from_account_canonical": "1234567890123",
    "to_account_canonical": "9876543210987",
    "transaction_type": "debit",
    "amount_band": "large",
    "channel": "NPSB",
    "from_account_age_days": 20,
    "from_cross_bank_count": 3
  },
  "cross_bank_flag": true,
  "request_id": "ae5346523baa42beb9e1b967affe978e",
  "latency_ms": 142
}
```

### Decision bands

| Score | Decision | Recommended bank action |
|---|---|---|
| `0–29` | `approve` | Process the transaction normally. |
| `30–59` | `review` | Process but route to next-day analyst review (CAMLCO queue). |
| `60–79` | `hold` | Pause processing, surface to analyst, decide within SLA. |
| `80–100` | `reject` | Block immediately, draft STR. |

**Bands are enforceable at the bank's discretion.** Kestrel returns the recommendation; the bank's core-banking system can override based on its own policy. The full audit trail (request payload + score + decision + reasons + your override) lives in `realtime_scoring_log` and `audit_log`.

### Reason codes

Each reason maps to a deterministic rule contribution. Treat these as stable contracts — Kestrel will add new rule codes over time, but existing codes keep their semantics:

| Rule | When it fires | Score contribution |
|---|---|---|
| `amount_large` | Amount ≥ 10 lakh BDT | +20 |
| `amount_very_large` | Amount ≥ 50 lakh BDT | +40 (replaces `amount_large`) |
| `structuring_suspect` | 9 lakh ≤ amount < 10 lakh (sub-CTR-threshold band) | +30 |
| `channel_cash_like` | Channel is `CASH` / `CHEQUE` / `DRAFT` | +15 |
| `channel_mfs` | Channel is `MFS_BKASH` / `MFS_NAGAD` / `MFS_ROCKET` | +8 |
| `new_account_high_value` | Originating account opened < 30 days ago AND amount ≥ 10 lakh | +20 |
| `from_entity_flagged` / `to_entity_flagged` | Either party already in the shared entities pool with risk_score ≥ 50 | scaled to `entity.risk_score × 0.3`, clamped to `[10, 30]` |
| `from_cross_bank_flagged` / `to_cross_bank_flagged` | Either party reported by 2+ institutions in the matches table | +15 (2 banks) or +25 (3+ banks) |

The final `score` is the sum of all contributions, clamped `[0, 100]`. The `confidence` field grows with the count of independent reasons (capped at 0.95).

### cURL example

```bash
curl -X POST https://kestrel-engine.onrender.com/transactions/score \
  -H "Authorization: Bearer $KESTREL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "BNK-TXN-000123456",
    "from_account": "1234567890123",
    "to_account": "9876543210987",
    "amount": 1750000,
    "currency": "BDT",
    "channel": "NPSB",
    "transaction_type": "debit",
    "timestamp": "2026-05-05T08:30:00+06:00"
  }'
```

### Python example

```python
import os
import httpx

BASE_URL = "https://kestrel-engine.onrender.com"
TOKEN = os.environ["KESTREL_TOKEN"]


def score_transaction(payload: dict) -> dict:
    with httpx.Client(timeout=2.0) as client:
        response = client.post(
            f"{BASE_URL}/transactions/score",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


result = score_transaction({
    "transaction_id": "BNK-TXN-000123456",
    "from_account": "1234567890123",
    "to_account": "9876543210987",
    "amount": 1750000,
    "currency": "BDT",
    "channel": "NPSB",
    "transaction_type": "debit",
})

if result["decision"] in ("hold", "reject"):
    queue_for_review(result["log_id"], result["reasons"])
elif result["decision"] == "review":
    log_for_analyst(result["log_id"])
# else: approve and continue
```

---

## 3. Feedback loop

```
POST /transactions/score/{log_id}/feedback
```

Once your analyst has reviewed a held / rejected transaction, report the ground-truth outcome. This is the foundation for the ML feedback loop on Kestrel's sovereign-AI track — the more truthful labels you feed back, the better the model gets at scoring your bank's traffic.

### Request

```json
{
  "outcome": "fraud",
  "note": "Confirmed fraud — case KST-2605-00041 opened, funds frozen at receiving bank."
}
```

| Field | Required | Notes |
|---|---|---|
| `outcome` | yes | One of `legitimate`, `fraud`, `unsure`. |
| `note` | no | Free-form rationale, max 1000 chars. Stored in `audit_log.details`. |

### Response

```json
{
  "id": "6997af82-8513-436f-8ffe-2c921afeecab",
  "feedback_received": true,
  "feedback_outcome": "fraud",
  "feedback_at": "2026-05-05T09:14:33+00:00"
}
```

The endpoint is idempotent — reporting feedback twice for the same `log_id` overwrites the prior outcome and stamps a fresh `feedback_at`. RLS guarantees a bank can only edit feedback on its own scoring rows.

---

## 4. Recent activity feed

```
GET /transactions/score/recent?limit=50
```

Returns the most recent scoring rows for the caller's org (or system-wide for regulator persona). Backs the live dashboard at `/monitoring/realtime`. Useful when you want to verify a specific call landed, audit decisions, or build your own internal dashboards on top of Kestrel.

```
GET /transactions/score/metrics?window_hours=24&top_limit=5
```

Returns aggregated metrics for the dashboard: decision distribution, latency percentiles (`p50`, `p95`, `p99`, `avg`), cross-bank flag count, and the top-scored transactions in the last hour. `window_hours` accepts `1–168` (1 hour to 7 days).

---

## 5. Error envelope

Every error response carries this shape:

```json
{
  "detail": "Insufficient role",
  "request_id": "ae5346523baa42beb9e1b967affe978e",
  "timestamp": "2026-05-05T06:28:59Z"
}
```

`request_id` is also echoed in the `X-Request-ID` response header. Always log it — Kestrel's structured JSON logs are keyed by request ID, so any support investigation will start from this value.

| Status | Meaning |
|---|---|
| `400` | Malformed `log_id` (must be a UUID). |
| `401` | Missing or expired `Authorization` token. |
| `403` | Token authenticated but the role lacks permission (`require_roles("manager","admin","superadmin","analyst")`), or attempt to feedback another org's row. |
| `404` | `log_id` does not exist. |
| `422` | Request body failed validation — bad `channel`, missing field, malformed `outcome`. |
| `500` | Internal error. Retry once after a 1-second backoff; if it persists, raise with support including the `request_id`. |
| `503` | Engine is bootstrapping (rare — usually during a deploy rotation). Retry after 10 seconds. |

---

## 6. Latency expectations & retry semantics

- **Target: p50 < 200 ms / p99 < 500 ms.** Achievable in production because the scorer runs read-only against indexed tables (`entities (entity_type, canonical_value)` and `matches (match_type, match_key)`).
- **Connection budget:** the engine runs FastAPI on `uvicorn` behind Render's edge, with HTTP/2 and TLS keep-alive on. Banks should use connection pooling (e.g. `httpx.Client` reuse) and *never* call the API serially in a loop without pooling.
- **Retry policy:**
  - `5xx` (excluding `503`) — retry once with exponential backoff (1s, then 4s). Do not retry indefinitely.
  - `503` — retry after 10s; this is a brief deploy rotation and usually resolves within 30s.
  - `4xx` — do **not** retry. Fix the request payload and resubmit.
- **Idempotency:** scoring is idempotent at the transaction-decision level — re-scoring the same `transaction_id` is safe and creates a new audit row each time. Use this to verify integration end-to-end without polluting an in-flight ledger.

---

## 7. Local audit & UI surface

Every successful scoring call lands in two tables your tenant can see:

- `realtime_scoring_log` — the full payload + decision + reasons + latency. RLS: own-org or regulator. Update is restricted to own-org (the feedback endpoint).
- `audit_log` — `action='realtime.score'` + the decision summary. Same RLS.

The web app surfaces both at `/monitoring/realtime`. The page auto-refreshes every 30 seconds and shows decision distribution, latency p50/p95/p99, top-scored transactions in the last hour, and the most recent activity stream. Bank persona sees its own institution; regulator persona sees the cross-system aggregate.

---

## 8. Sanctions / PEP / adverse-media screening

```
POST /screening/entity
```

Fuzzy-matches a candidate (name + optional DOB / nationality / NID / passport) against the shared `watchlist_entries` pool — OFAC SDN, UN consolidated, UK OFSI, EU consolidated, Bangladesh Bank's domestic list, and PEP. Returns matches scored 0–1 across the four signals (name 0.4 / DOB 0.3 / nationality 0.2 / identifier 0.1).

### Request

```json
{
  "name": "Mohammad Karim",
  "date_of_birth": "1979-03-14",
  "nationality": "BD",
  "nid": "1979314001234",
  "passport": "BR9912345",
  "screening_lists": ["OFAC", "UN", "UK_OFSI", "BB_DOMESTIC", "PEP"],
  "minimum_match_score": 0.7
}
```

`screening_lists` is optional — omit to search every list. `minimum_match_score` defaults to 0.7; lower it to widen the search at the cost of more false positives.

### Response

```json
{
  "matches": [
    {
      "list_source": "OFAC",
      "list_version": "synthetic-2026-05-05",
      "entry_id": "...",
      "entry_type": "individual",
      "matched_name": "Mohammad Karim",
      "matched_aliases": ["M. Karim", "Mohammad Hossain Karim"],
      "matched_entry": {
        "primary_name": "Mohammad Karim",
        "aliases": ["M. Karim", "Mohammad Hossain Karim"],
        "date_of_birth": "1979-03-14",
        "nationality": "BD",
        "identifiers": {"passport": ["BR9912345"], "nid": ["1979314001234"]},
        "addresses": [{"city": "Dhaka", "country": "Bangladesh"}],
        "reason": "SDN-FORMER-MILITARY"
      },
      "match_score": 0.94,
      "match_reasons": [
        "primary_name fuzzy match similarity=0.99",
        "date_of_birth exact match",
        "nationality match",
        "identifier match"
      ]
    }
  ],
  "screened_at": "2026-05-05T07:32:14+00:00",
  "request_id": "..."
}
```

### Inline integration with /transactions/score

When `from_account_metadata` or `to_account_metadata` carries a `name` field, the realtime scoring path runs the same screening service inline. A hit at `match_score >= 0.7` adds a `from_sanctions_hit` (or `to_sanctions_hit`) reason worth +50 points — enough on its own to push the transaction score into the `hold` band, and two hits push it past `reject`. The matched list source + score are echoed in `evidence.{from,to}_sanctions_hit`.

This is the recommended way to integrate screening into a core-banking pipeline: send the candidate name on every transaction, let scoring fold in the result, and drive your bank's response off the unified `decision`. Standalone calls to `/screening/entity` remain available for manual analyst workflows.

```
POST /screening/adverse-media
```

ComplyAdvantage adapter for adverse-media screening. Returns `{provider: "stub", hits: []}` when `COMPLYADVANTAGE_API_KEY` is not configured. Same request shape as `/screening/entity` minus the identifier fields.

```
GET /screening/entries?list_source=OFAC&limit=50
```

Browse the watchlist pool. Any authenticated user can read. Useful for verifying ingestion ran and for an analyst to see the most recent additions.

```
POST /screening/entries
```

Manual upload — restricted to regulator-org admins (Bangladesh Bank's domestic watchlist is the primary use case; OFAC / UN / UK OFSI / EU come through the daily ingestion task). The `Bangladesh Bank Domestic Watchlist` source uses `list_source: "BB_DOMESTIC"`.

### cURL example

```bash
curl -X POST https://kestrel-engine.onrender.com/screening/entity \
  -H "Authorization: Bearer $KESTREL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mohammad Karim",
    "date_of_birth": "1979-03-14",
    "nationality": "BD",
    "minimum_match_score": 0.7
  }'
```

---

## 9. KYC / CDD onboarding

The customer-onboarding flow runs sanctions screening (Phase 4) inline against the customer + every beneficial owner, composes a customer-level risk score, and persists the row with the full screening result for audit.

```
POST /customers
```

### Request

```json
{
  "customer_external_id": "CUST-100345",
  "customer_type": "individual",
  "full_name": "Mohammad Karim",
  "nid": "1979314001234",
  "passport": "BR9912345",
  "date_of_birth": "1979-03-14",
  "nationality": "BD",
  "phone": "+880 1711-555-001",
  "email": "mkarim@example.test",
  "address": {"city": "Dhaka", "country": "Bangladesh"},
  "metadata": {"source": "branch-walkin"},
  "beneficial_owners": []
}
```

For `customer_type: "business"`, `beneficial_owners` is an array of `{full_name, nid, passport, date_of_birth, nationality, ownership_pct}` objects. Each owner is screened separately; their hits roll into the composed risk score.

### Response

```json
{
  "id": "0a8e8f6d-…",
  "customer_external_id": "CUST-100345",
  "customer_type": "individual",
  "full_name": "Mohammad Karim",
  "risk_score": 95,
  "risk_level": "declined",
  "kyc_status": "declined",
  "screening_results": {
    "screened_at": "2026-05-05T08:14:33+00:00",
    "primary": [
      {
        "list_source": "OFAC",
        "list_version": "synthetic-2026-05-05",
        "entry_id": "...",
        "matched_name": "Mohammad Karim",
        "match_score": 0.94,
        "match_reasons": ["primary_name fuzzy match similarity=0.99", "date_of_birth exact match", "nationality match", "identifier match"]
      }
    ],
    "beneficial_owners": {}
  },
  "onboarded_at": "2026-05-05T08:14:33+00:00",
  "last_rescreened_at": "2026-05-05T08:14:33+00:00"
}
```

### Decision bands

| Composed score | risk_level | kyc_status |
|---|---|---|
| `0–29` | `low` | `approved` |
| `30–59` | `medium` | `approved` (with watchlist note) |
| `60–79` | `high` | `review` (queued for CAMLCO review) |
| `>= 80` | `declined` | `declined` |

A direct sanctions hit at score `>= 0.9` on the primary customer forces `kyc_status=declined` regardless of the composed score — onboarding a sanctioned party at any composed score is itself a regulatory violation.

### Other endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/customers?risk_level=high&kyc_status=review&limit=100` | List with filters. |
| `GET` | `/customers/{id}` | Detail with full screening_results. |
| `PATCH` | `/customers/{id}` | Update phone / email / address / metadata / beneficial_owners. |
| `POST` | `/customers/{id}/review` | CAMLCO review action (`{"decision": "approved" \| "declined" \| "review", "note": "..."}`). |
| `POST` | `/customers/{id}/rescreen` | Re-run sanctions screening on demand. |

### Periodic re-screening

A daily Celery Beat task at 03:00 BDT (after the 02:30 watchlist refresh) sweeps approved + review customers whose `last_rescreened_at` is missing or older than 7 days, re-runs sanctions, and escalates new score `>= 0.9` hits as `source_type='kyc_rescreen'` alerts plus `variant='escalated'` cases. Operationally: if OFAC publishes a new SDN entry on Wednesday and one of your existing customers matches, you'll see an alert in your queue by Thursday morning.

---

## 10. Public status surface

```
GET /status/summary       — public, no auth
GET /status/incidents     — public, no auth
GET /status/plans         — public, no auth
```

Drives the public status page at `kestrel-nine.vercel.app/status`. The summary returns:

```json
{
  "status": "up",
  "components": [
    {"component": "auth", "status": "up", "uptime_30d": 0.9989, "uptime_90d": 0.9974, "observed_at": "...", "detail": "..."},
    {"component": "database", "status": "up", "uptime_30d": 0.9999, ...},
    ...
  ],
  "incidents": [
    {"id": "...", "severity": "minor", "component": "ai", "summary": "...", "is_active": false, ...}
  ],
  "overall_uptime_30d": 0.9991,
  "generated_at": "..."
}
```

Uptime is computed from the `uptime_pings` ledger (5-minute Beat task). Incidents are manually posted by regulator-org admins via `/admin/status/incidents`.

### Pricing tier enforcement

`GET /status/plans` returns the three plans defined in `engine/app/services/billing.py` — banks-direct landing reads this so any code-level price change flows through automatically.

When a starter-tier tenant calls a paid feature (`/transactions/score`, `/screening/entity`, `/screening/adverse-media`, `/customers`), the engine returns:

```
HTTP/1.1 402 Payment Required
{
  "detail": "Feature 'realtime' is not included in the Starter plan. Contact procurement to upgrade.",
  "request_id": "...",
  "timestamp": "..."
}
```

`GET /admin/status/plan` (authed) returns the caller's resolved plan + per-tenant overrides — useful when an integration team is debugging "why am I getting 402?".

---

## 11. Versioning & change log

This API is **v1 stable**. Future additions (KYC-driven base risk, sovereign-AI confidence routing) will appear as additive fields in the response, never as breaking changes. Reason codes, decision bands, and field shapes are durable contracts.

| Date | Change |
|---|---|
| 2026-05-05 | V2 phase 3 — initial public release of `/transactions/score`, `/transactions/score/{id}/feedback`, `/transactions/score/recent`, `/transactions/score/metrics`. |
| 2026-05-05 | V2 phase 4 — sanctions / PEP / adverse-media screening: `/screening/entity`, `/screening/adverse-media`, `/screening/entries` (GET browse + POST manual upload). New reason classes `from_sanctions_hit` / `to_sanctions_hit` (+50 each) on `/transactions/score`. |
| 2026-05-05 | V2 phase 5 — KYC / CDD onboarding: `POST /customers`, `GET /customers`, `GET /customers/{id}`, `PATCH /customers/{id}`, `POST /customers/{id}/review`, `POST /customers/{id}/rescreen`. Inline sanctions screening on customer + beneficial owners. Daily re-screening Beat task at 03:00 BDT. |
| 2026-05-05 | V2 phase 6 — Public status surface: `GET /status/{summary,incidents,plans}` (no auth) + `POST /admin/status/incidents` + `POST /admin/status/incidents/{id}/resolve`. Pricing-tier 402 PAYMENT REQUIRED on `/transactions/score`, `/screening/entity`, `/screening/adverse-media`, `/customers` for starter-tier tenants. New Beat jobs: `uptime_ping_5min` and `weekly_demo_refresh`. |

---

## 12. Support

Procurement / pilot conversations: `kamal@enso-intelligence.com`. Engineering integration support: `engineering@enso-intelligence.com`. Always include the `request_id` from the response envelope.
