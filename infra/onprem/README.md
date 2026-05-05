# Kestrel on-prem packaging (V3 P6)

The framework for deploying Kestrel inside a customer's data centre or
VPC. Same engine + web binary as the cloud Render deploy; air-gapping
is a configuration concern, not a code path.

See `docs/onprem-deployment.md` for the operator-facing guide. This
directory is the build context.

| File                       | Purpose                                                  |
|----------------------------|----------------------------------------------------------|
| `Dockerfile.engine`        | Multi-stage image: FastAPI + Celery worker + Beat        |
| `Dockerfile.web`           | Next.js 16 standalone build                              |
| `docker-compose.yml`       | Postgres + Redis + engine + worker + beat + web + Caddy  |
| `Caddyfile`                | TLS termination + `/api/*` → engine, everything else → web |
| `scripts/bootstrap.py`     | Idempotent migration runner; runs on engine container start |
| `scripts/entrypoint-*.sh`  | Engine / worker / beat entrypoints                       |
| `examples/.env.example`    | Operator-editable env template                           |
| `examples/license.yaml`    | License file template (mounts at /etc/kestrel/license.yaml) |

## Build context

Both Dockerfiles take the **repo root** as build context so the
`engine/` and `supabase/migrations/` directories are visible:

```bash
cd /opt/kestrel
docker build -f infra/onprem/Dockerfile.engine -t kestrel-engine:onprem .
docker build -f infra/onprem/Dockerfile.web    -t kestrel-web:onprem .
```

Or via `docker compose build` from `infra/onprem/`, which already sets
`context: ../..` per service.

## What is not in this directory

- IdP integration shims (OIDC / SAML). Driven by first customer.
- Cosign signing + SBOM attestation. Driven by first customer.
- HA topology overrides. Single-VM is the baseline.
