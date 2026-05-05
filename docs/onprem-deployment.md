# Kestrel on-prem deployment

This guide is for institutions that need Kestrel running inside their own
data centre or VPC — typically foreign-bank subsidiaries operating under
home-jurisdiction policy, or Tier-3 banks with a hard "no SaaS" mandate.

The on-prem image is the same engine + web binary that runs on Render. We
**package**, we don't fork. Air-gapping is a configuration concern: the
engine drops outbound AI providers (OpenAI / Anthropic) when
`KESTREL_DEPLOYMENT_MODE=onprem`, and the operator imports the watchlist
feeds via USB instead of letting the Beat task pull from the internet.

This document describes the framework that ships in V3 phase 6. Customer
acceptance, IdP integration, and signed/notarised images are follow-up
tasks driven by the first signed Tier-3 customer.

---

## Bill of materials

One VM (or appliance) running:

| Service     | Purpose                                          | Image                       |
|-------------|--------------------------------------------------|-----------------------------|
| `postgres`  | Application database                             | `postgres:16-alpine`        |
| `redis`     | Celery broker + cache                            | `redis:7-alpine`            |
| `engine`    | FastAPI application (uvicorn)                    | `kestrel-engine:onprem`     |
| `worker`    | Celery worker                                    | `kestrel-engine:onprem`     |
| `beat`      | Celery beat scheduler                            | `kestrel-engine:onprem`     |
| `web`       | Next.js 16 (standalone output)                   | `kestrel-web:onprem`        |
| `caddy`     | TLS termination + reverse proxy                  | `caddy:2-alpine`            |

A separate GPU box (recommended; not required) running vLLM serves the
sovereign model. The engine reaches it on the LAN via `AI_SOVEREIGN_URL`.

Customer-side requirement: Docker Engine 24+ with the Compose plugin.
Total disk footprint at first boot is ≈ 4 GB; CPU/RAM scale with active
transaction volume — a Tk-100-crore-month bank fits comfortably on
8 vCPU / 32 GB RAM.

---

## First boot

```bash
# On the on-prem VM, with the Kestrel source tree already at /opt/kestrel.

cd /opt/kestrel/infra/onprem

# 1. Configuration.
cp examples/.env.example .env
# Edit .env: POSTGRES_PASSWORD, KESTREL_PUBLIC_HOST, AI_SOVEREIGN_URL.

# 2. License file. Issued per-customer by Kestrel HQ.
sudo mkdir -p /etc/kestrel
sudo cp examples/license.yaml /etc/kestrel/license.yaml
sudo chown root:root /etc/kestrel/license.yaml
sudo chmod 0644 /etc/kestrel/license.yaml

# 3. First start — builds engine + web images + applies migrations.
docker compose up --build -d

# 4. Health check.
curl -fsS https://kestrel.local/ready -k | jq .
```

The `engine` container runs `kestrel-bootstrap` on entry. It applies
every migration in `supabase/migrations/*.sql` against the on-prem
Postgres in order, idempotent via `supabase_migrations.schema_migrations`.
Engine `restart: unless-stopped` ensures the container loops until the
DB schema is current — a partial migration won't accept traffic.

Service URLs:

| Path                    | Backed by  |
|-------------------------|------------|
| `https://kestrel.local` | web (3000) |
| `/api/...`              | engine (8000) — proxied by Caddy |
| `/health`, `/ready`     | engine (8000) — direct |

Caddy uses its internal CA by default (self-signed). When the customer
provides a real cert chain or a publicly reachable hostname, swap the
`tls internal` directive in `Caddyfile`.

---

## On-prem AI configuration

Onprem mode strips OpenAI + Anthropic from every AI route chain. The
remaining providers in the chain are:

1. **Sovereign** (when `AI_SOVEREIGN_URL` + `AI_SOVEREIGN_MODEL` are set
   AND a row in `sovereign_rollout` flips a task's `rollout_pct` above
   0). Customer's GPU box runs vLLM with the sovereign adapter loaded.
2. **Heuristic** — always present as the floor. Adequate for STR
   drafting and entity extraction; degraded for narrative generation
   where the sovereign adapter is the production path.

There is no Claude fallback in onprem mode. If the sovereign endpoint
is unreachable, the heuristic provider answers — never an outbound call.

To start serving sovereign traffic on a single task:

```sql
-- On the on-prem Postgres, as the BYPASSRLS engine user.
INSERT INTO sovereign_rollout (task_name, threshold, rollout_pct, reason, updated_by)
VALUES ('alert_explanation', 0.75, 10, 'first task in production', 'ops')
ON CONFLICT (task_name) DO UPDATE
SET threshold = excluded.threshold,
    rollout_pct = excluded.rollout_pct,
    reason = excluded.reason,
    updated_by = excluded.updated_by,
    updated_at = now();
```

Routing + outcome logging + Beat-driven rollback are wired identically
to cloud. The promotion harness (`infra/training/promote_sovereign_adapter.py`)
must clear before flipping `rollout_pct` above 0.

---

## Air-gapped watchlist sync

In onprem mode the daily Beat task `app.tasks.screening_tasks.refresh_all`
remains gated behind `KESTREL_WATCHLIST_INGESTION_ENABLED=true`. If the
customer permits outbound to the OFAC / UN / UK feed URLs, set the env
var and the Beat task will pull as usual.

If the customer is fully air-gapped, ship the feeds via USB / NFS:

```bash
# On a workstation with internet access:
mkdir watchlist-2026-05-05
curl -o watchlist-2026-05-05/sdn.xml          https://www.treasury.gov/ofac/downloads/sdn.xml
curl -o watchlist-2026-05-05/consolidated.xml https://scsanctions.un.org/resources/xml/en/consolidated.xml
curl -o watchlist-2026-05-05/UK-Sanctions-List.csv https://docs.fcdo.gov.uk/docs/UK-Sanctions-List.csv

# On the customer site, after copying watchlist-2026-05-05 to the VM:
docker compose exec engine \
  python -m scripts.import_watchlist_archive \
    --archive /var/lib/kestrel/watchlist/watchlist-2026-05-05
```

The script uses the same parsers as the live Beat task, the same
deterministic UUID5 PKs, and the same `ON CONFLICT DO NOTHING` upsert,
so re-running the same archive is a no-op. Use `--dry-run` first to
verify file recognition without touching the database.

---

## License + telemetry

The license file at `/etc/kestrel/license.yaml` is read on engine
start. It maps to the same `Plan` / `TenantPlan` abstraction used in
cloud: `plan_id` selects the feature bundle, `plan_overrides` enables
specific features on top of the plan. Overrides cannot disable a
plan-included feature (matches cloud semantics).

The license file is a configuration artefact, not a cryptographic one.
Tampering protection is the customer's responsibility (file-system
permissions on `/etc/kestrel/`). The engine logs a warning when the
license is within 30 days of `expires_at` and a louder warning after
expiry. **Service does not stop on expiry** — operators do not lose
access to compliance data because of a billing dispute.

Telemetry pingback (`app.tasks.telemetry_tasks.pingback`, daily 01:00 BDT)
is **off by default** in onprem mode. Set:

- `KESTREL_TELEMETRY_ENABLED=true`
- `KESTREL_TELEMETRY_URL=https://hq.kestrel/ping`

…to opt in. Posted payload is aggregate counts only (organisations,
transactions, alerts_open, submitted-STRs-30d, AI-invocations-30d) —
no PII, no business content. Designed to satisfy a procurement reviewer.

---

## Backup + restore

Kestrel doesn't ship a custom backup tool — Postgres `pg_dump` and the
Docker volume backup pattern cover it. Recommended cadence:

```bash
# Daily, at 23:00 BDT (after the operational day closes).
docker compose exec -T postgres \
  pg_dump -U kestrel -F c -d kestrel \
  > /var/backups/kestrel-$(date +%Y%m%d).dump
```

Watchlist data (`watchlist_entries`) is reproducible from the upstream
feeds via `import_watchlist_archive.py`, so it does not need its own
backup track.

---

## Disabling demo mode

On-prem first-boot defaults `KESTREL_ENABLE_DEMO_MODE=true` so the
operator can verify the install before customer auth integration. Once
the customer's IdP is wired (typically OIDC against their AD/Entra
tenant — Phase-6 follow-up) flip both `KESTREL_ENABLE_DEMO_MODE` and
`NEXT_PUBLIC_ENABLE_DEMO_MODE` to `false` and restart.

---

## What is NOT covered by this document (yet)

- IdP integration. Cloud uses Supabase Auth; on-prem will need OIDC or
  SAML against the customer's directory. Driven by the first signed
  Tier-3 customer.
- Image signing + notarisation. Customers in regulated environments
  will require Cosign-signed images and an SBOM attestation.
- HA topology. Single-VM install is the baseline; multi-node with
  external Postgres + Redis is a customer-pull engagement.

These will land alongside the first on-prem rollout, not before.
