# SentinelAI on Supabase (D-053)

## Why

SentinelAI's default `DATABASE_URL` is a local SQLite file — fine for local
dev, wrong for a cloud deployment: a Render/Fly/etc. instance's local disk
isn't shared across services or restarts-with-a-new-disk, and it can't be
the same database two separate services (`proxy`, `gateway`) both write to.
Supabase (managed Postgres) fixes that: one durable, shared, network-reachable
database, and the connection string is a platform secret — never a file in
the repo, never something a CLI or client needs to hold.

**No code changed to make this possible; the app was already
database-agnostic.** The one real bug found and fixed: `proxy/db/session.py`
was unconditionally passing `check_same_thread=False` to the DB driver —
that's a SQLite-only (`pysqlite`) connect argument; `psycopg2` raises a
`TypeError` if you pass it. Fixed to only pass it for `sqlite://` URLs.

## Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com) (free tier is enough to start).
2. **Get the connection string**: Project Settings → Database → Connection string → URI. Use the **pooler** connection (port 6543, `?pgbouncer=true`) for a serverless/many-short-connections host like Render's free tier; use the **direct** connection (port 5432) if the host keeps a long-lived process with a small, stable connection count. Either works with SQLAlchemy — start with the pooler string unless you hit issues.
3. **Never put the real connection string in a file that gets committed.** Locally: put it in `.env` (already gitignored) as `DATABASE_URL=postgresql://postgres:[password]@[host]:6543/postgres?pgbouncer=true`. On Render: set it as the `DATABASE_URL` environment variable value directly in the Render dashboard — `deploy/render.yaml` declares it as `sync: false`, meaning Render prompts for the value once and stores it as a platform secret, never in the repo.
4. **Install the driver**: `psycopg2-binary` is already in `requirements.txt` — a normal `pip install -r requirements.txt` picks it up (Render's `buildCommand` already does this).
5. **Create the tables**: nothing to run by hand. Every SentinelAI service calls `init_db()` on startup (`proxy/main.py`), which does `Base.metadata.create_all(engine)` — this creates all 10 tables (`users`, `workspaces`, `projects`, `call_logs`, `findings`, `test_run_results`, `agent_action_logs`, `security_events`, `project_api_keys`, `baselines`) the first time the proxy boots against the new `DATABASE_URL`, and is a no-op on every boot after that. Just start the proxy once with `DATABASE_URL` pointed at Supabase and the tables appear. (Verified directly via the Supabase MCP against project `eaapkdcsufyeunmmiizv` on 2026-09-24 — schema applied, empty, no live proxy has run against it yet.)
   - Supabase auto-enables Row Level Security with no policies on every new table — this is expected and harmless here: SentinelAI's own auth (`proxy/auth.py`) connects directly with the Postgres role (which owns the tables and bypasses RLS), never through Supabase's PostgREST/anon/authenticated roles or client SDK. RLS-with-no-policy only blocks access this app never uses.
6. **Point the gateway at the same instance** (optional): set the gateway service's `DATABASE_URL` to the *same* Supabase connection string as the proxy, then flip `GATEWAY_RECORD_EVENTS=true`. This is what makes gateway-side monitoring events (D-050) land in the same shared `security_events` table the dashboard already reads — without a shared DB, gateway events would have nowhere durable to go, which is why this stayed off by default until now.

## What doesn't need to change

- **The SDK/CLI never touches the database at all** — `scripts/sentinel_ci.py` talks to the proxy over HTTP only (`POST /v1/findings/sync`, `GET /v1/regression-report`), so there was never a DB secret in the CLI to leak in the first place (D-047). This migration doesn't change that; it just makes the *server-side* storage shared and durable instead of local-disk SQLite.
- **The web frontend never touches the database directly** — it calls the proxy's/gateway's HTTP API, same as always.
- **Local development stays on SQLite by default** (`.env.example`) — no reason to require a real Supabase project just to run tests or develop locally. Point `DATABASE_URL` at Supabase only when you actually deploy, or if you want to test against Postgres locally.

## Rollback

`DATABASE_URL` is the only thing that changed. Set it back to a local
`sqlite:///...` path and restart — SentinelAI has no Postgres-only feature;
`Base.metadata.create_all()` works identically against either backend.
