# Capstone: Checkout Investigator (local)

A Copilot SDK agent that finds why a checkout failed and proposes a fix that a human approves.
Full explanation: [docs/capstone.md](../../docs/capstone.md).

```text
web (React, :5173) → api (FastAPI, :8000) → agent (Copilot SDK, :8001) → Foundry gpt-5.4-mini (BYOK)
                                     └────────────→ db (Postgres, :5432) ←──────┘
```

## Prerequisites

- Docker with Compose.
- `az login` on the host. The agent mounts `~/.azure` read-only and uses `AzureCliCredential`.
- A Foundry resource with a reasoning model deployment (`gpt-5.4-mini`). Your user needs the **Cognitive Services OpenAI User** role.
- About 25K input tokens per investigation. Give the deployment enough TPM (10K TPM causes slow 429 retries).

## Run

```bash
cd lessons/capstone
cp .env.example .env                 # fill in FOUNDRY_BASE_URL (never commit .env)
./make_secrets.sh                    # once: random DB passwords in ./secrets (git-ignored)
./agent/fetch_wheels.sh              # once: downloads the SDK wheel (not on the package mirror; git-ignored)
docker compose up -d --build
docker compose ps                    # agent shows (healthy)
```

Open <http://localhost:5173>. Pick order **1000**, click **Investigate**, then approve or reject the fix.

| Order | Seeded story | Expected finding |
|---|---|---|
| 1000 | Reservation RES-77 expired before payment capture | `RESERVATION_EXPIRED` |
| 1001 | Normal checkout | `NO_FAILURE` (no fix) |
| 1002 | Card declined, insufficient funds | `CARD_DECLINED` |
| 1003 | Order on a fraud hold | `FRAUD_HOLD` |

## Test

```bash
docker compose run --rm --no-deps agent pytest -q        # guards, harness, DB tools (needs db up)
docker compose run --rm --no-deps -e APPLICATIONINSIGHTS_CONNECTION_STRING= api pytest -q
docker compose run --rm --no-deps web npm run -s build   # type check + build
```

## Package feeds

Containers on this laptop cannot do a TLS handshake with public PyPI or npm. The images use the Microsoft feeds:

- Python: `ARG PIP_FEED=https://packagefeedproxy.microsoft.io/pypi/simple/` (in `agent/` and `api/` Dockerfiles).
- npm: `web/.npmrc`.

The mirror has no `github-copilot-sdk==1.0.16`, so `agent/wheels/` holds it (`fetch_wheels.sh`). Change `SDK_VERSION` to fetch another version. Do not force the mirror on Foundry Hosted Agents.

## Layout

```text
agent/   Copilot SDK harness: harness.py (session config), hooks.py, tools.py, logs_mcp_server.py, skills/
api/     FastAPI: health, orders, fixes, SSE relay for investigate and decision
web/     React + Vite + TypeScript UI
db/init/ schema, seed data, read-only and read-write roles
```

## Passwords

- DB passwords are files in `secrets/`, made by `./make_secrets.sh`. Compose mounts them at `/run/secrets/` (not env vars, so they do not show in `docker inspect`).
- Rotate an app password: `rm secrets/app_ro_password && ./make_secrets.sh && docker compose up -d --force-recreate`. The `db-roles` step runs `ALTER ROLE` on every start.
- The superuser password (`postgres_password`) is set only when the volume is new. Changing it needs a reset.

## Reset

```bash
docker compose down -v      # also deletes the database and saved SDK sessions
```
