# Run the complete application

Install and start Docker Desktop with Linux containers and Docker Compose v2.
From the repository root:

```powershell
docker compose up --build
```

Open **http://localhost:8081**. No Node or Python installation, `.env` file, API key,
or manually created password is required for this Compose setup.

There are only two services:

- `db`: PostgreSQL 17, with its data in the `postgres_data` named volume. Its port
  is not published to the host.
- `app`: a multi-stage image builds React with Node, then copies only its static
  output into the Python/FastAPI runtime. Host port **8081** maps to container port
  8000. FastAPI serves the UI, HTTP API, and WebSocket on the same origin.

The root `config.yml` is mounted read-only and loaded at application startup.
Change it, then use `docker compose restart app` to apply new parameters. This
starts a new experiment. The default requires three human participants; test with
separate browser profiles, or configure one human and two AI players for a solo
walkthrough. Do not run more than one application worker or replica.

## Verify startup and connectivity

In another terminal:

```powershell
docker compose ps
docker compose logs --tail=50 app db
Invoke-RestMethod http://localhost:8081/health
docker compose exec db pg_isready -U experiment -d experiment
docker compose exec db psql -U experiment -d experiment -c "SELECT id, phase, round, status, results FROM sessions ORDER BY created_at DESC;"
```

Both containers should become healthy. `/health` should return
`{"status":"ok","database":"ok"}`; it executes `SELECT 1` using the application's
database connection. The app fails startup if configured database access fails,
instead of silently running without persistence. Compose waits for PostgreSQL's
healthcheck before starting the app, using Docker's documented
[dependency health condition](https://docs.docker.com/compose/how-tos/startup-order/).

Join, send a chat message, vote, and complete the experiment. Inspect records:

```powershell
docker compose exec db psql -U experiment -d experiment -c "SELECT session_id, player, round, text FROM messages ORDER BY created_at;"
docker compose exec db psql -U experiment -d experiment -c "SELECT session_id, player, round, target FROM votes ORDER BY created_at;"
docker compose exec db psql -U experiment -d experiment -c "SELECT id, status, results FROM sessions ORDER BY created_at DESC;"
```

To check retention, run `docker compose restart app` and repeat the queries. Prior
rows remain, and a new waiting-room session appears. `docker compose down` stops
the deployment while keeping its volumes. **`docker compose down -v` deletes both
the research data and generated credential volume.**

## Minimal schema and write behavior

`backend/app/schema.sql` defines three tables, created idempotently at startup:

| Table | Stored data |
| --- | --- |
| `sessions` | UUID, timestamps, configuration snapshot, private AI label assignments, phase/round, status, and final results JSON containing totals and winner. |
| `messages` | Session ID, message ID, anonymous sender, round, text, timestamp. All committed messages are retained, even beyond the engine's 100-message reconnect history. |
| `votes` | Session ID, voter, round, target, timestamp. A primary key enforces one vote per player per round. |

No additional results table is needed because each session has one final result.
No tokens are persisted or exposed by database inspection endpoints; there are
no public endpoints for role/configuration records. SQL inspection is an operator
task, not a participant feature.

Psycopg uses bound parameters for values, including chat text, and explicit
transactions for each accepted action plus the session update. See
[Psycopg parameter binding](https://www.psycopg.org/psycopg3/docs/basic/params.html).
The hub persists validated actions before broadcasting their acknowledgements.
Session phase changes/results are persisted before state broadcasts. Countdown
ticks do not cause writes unless the phase, round, or results change.

The existing experiment engine is unchanged. The only HTTP integration addition
is `/api/join`, an alias for `/join`, because the built frontend uses that URL
without Vite's development proxy. Static serving is registered after API routes.
Only the build directory is served, not configuration or backend source files.

For this three-player assessment, writes are synchronous on the single server
loop; database latency can briefly delay updates. Queries and connection setup
have five-second timeouts. If a write fails, the session stops accepting actions,
connected clients are closed, and health becomes 503. Restart the app after fixing
the database. It does not claim success for uncommitted actions or continue with
inconsistent in-memory state. A connection failure at commit can leave an uncertain
last action; retained database rows are the record of what committed.

## Restart limitation

**Active sessions do not resume after an application restart.** Every startup
creates a new session UUID and marks previously active sessions `interrupted`.
Completed sessions keep their results. Previously committed messages, votes, and
results remain in PostgreSQL. In-flight actions may be lost; results are not
reconstructed for experiments interrupted before finalization.

Player tokens, socket bindings, monotonic deadlines, pending AI actions, and live
state remain in memory. Old reconnect tokens are invalid after restart; the UI
offers “Clear expired identity”, followed by a fresh join. Full recovery would
require durable identity bindings, restart-safe deadlines, and rehydrating the
engine. That work is deliberately deferred rather than adding a second state
machine in the database layer.

## Credentials and local development

The database bootstrap generates a random password once inside the `db_secret`
Docker volume. Both services read it from that volume; it never enters source,
the image build, or a Compose literal. PostgreSQL retains the same password as
long as its data volume exists, so retain/restore the credential volume with it.
Deleting only the credential volume will generate a mismatched password; do not
do this for an existing database. Docker host administrators can access these
volumes, as they can access the database itself.

For a non-Docker backend, set `DATABASE_URL` or standard PostgreSQL environment
variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD`).
`DB_PASSWORD_FILE` is supported instead of a password environment variable.
Keep real credentials outside tracked files. If neither `DATABASE_URL` nor
`PGHOST` is set, the original in-memory development mode remains available;
`/health` then returns only `{"status":"ok"}`.

Build with `npm ci` and `npm run build` in `frontend/` to serve the build from a
local FastAPI process. `STATIC_DIR` can override its default `frontend/dist` path.
The separate Vite development-server workflow also continues to work.

## Verification limits

All 25 backend tests passed against an isolated PostgreSQL 18 cluster, including
parameter binding, full message retention, final-result persistence, transactional
rollback, and restart marking. The cluster was stopped and removed afterward.
The Docker deployment targets PostgreSQL 17; that exact image was not run here.

Docker is not installed in the implementation environment, so the actual image
build and `docker compose up --build` could not be run here. The YAML, Dockerfile,
static/API integration, and repository tests were checked separately. Real
PostgreSQL tests can be enabled by setting `TEST_DATABASE_URL` before running:

```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Use a test database where the test user can create schemas. Tests create and
remove only their own unique `test_...` schema; otherwise PostgreSQL-specific tests
are skipped. The schema bootstrap supports a fresh/minimal schema, not automatic
migrations of future schema changes.
