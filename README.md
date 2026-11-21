# Human-AI Experiment Platform

A minimal three-player group decision-making experiment prepared for the Student
Research Assistant - Full-Stack Developer technical assessment at the Center for
Humans and Machines, Max Planck Institute. Participants discuss who should become
the Decision Maker and vote after each of two discussion rounds.

The application supports three humans, two humans plus one scripted AI player,
or one human plus two scripted AI players. Everyone appears as **Player A, B, or
C**. Public HTTP and WebSocket payloads omit human/AI roles.

## Quick start with Docker

Prerequisites: Docker Desktop running Linux containers, Docker Compose v2, and
host port **8081** available. From the repository root:

```sh
docker compose up --build
```

Open **http://localhost:8081**. The current working configuration is a solo demo:
**one human, two AI players, 60-second discussions, and 30-second voting phases**.
Joining starts the experiment immediately in this mode. Other configurations wait
for all required human participants.

Only two containers run: PostgreSQL and the application. The multi-stage Dockerfile
builds React, then FastAPI serves the resulting static files, API, and WebSocket
endpoint together. No separate frontend server, API key, or `.env` setup is needed.
A random database password is generated inside a Docker volume, never in source.

Check startup in another terminal:

```sh
docker compose ps
docker compose logs --tail=50 app db
docker compose exec db pg_isready -U experiment -d experiment
```

Open `http://localhost:8081/health`, or run in PowerShell:

```powershell
Invoke-RestMethod http://localhost:8081/health
```

Expected response: `{"status":"ok","database":"ok"}`. This checks the app's
database connection with `SELECT 1`. The Compose image build and startup have
**not been run in the development environment**, where Docker is unavailable.
See [DEPLOYMENT.md](DEPLOYMENT.md) for database inspection and restart checks.

## Technology stack

| Layer | Technology |
| --- | --- |
| UI | React 19, JavaScript, plain responsive CSS |
| Frontend build | Vite 7, npm lockfile |
| Server | Python 3.12 in Docker, FastAPI, Uvicorn, Pydantic |
| Real-time transport | Native browser WebSocket and FastAPI WebSocket endpoint |
| Storage | PostgreSQL 17 container, Psycopg 3 parameterized queries |
| Configuration | YAML parsed with PyYAML |
| Tests | Python unittest/FastAPI TestClient; Node's built-in test runner |
| Packaging | Docker multi-stage build and Docker Compose v2 |

## Architecture

```text
Browser: React UI + private reconnect token in localStorage
    | HTTP /api/join; WebSocket /ws
    v
FastAPI: API routes, authentication, static files, background ticker
    |
SessionHub: identity bindings, broadcasts, persistence, scripted-player adapter
    |                          |
    v                          v
ExperimentSession          PostgresStore
phase and voting rules     parameterized transactions
                               |
                               v
                           PostgreSQL
```

`backend/app/engine.py` owns the state machine independently of HTTP and SQL:

```text
Waiting -> Discussion 1 -> Voting 1 -> Discussion 2 -> Voting 2 -> Final Results
```

- The engine shuffles labels at creation and starts when all human slots are filled.
- A server ticker processes deadlines every 250 ms. Clients display the server's
  remaining time but cannot advance phases or choose their sender identity.
- Chat and votes from both humans and scripted players go through the same engine
  validation and hub broadcast methods.
- `storage.py` writes accepted actions before broadcasting them. `schema.sql`
  defines three tables: sessions, messages, and votes. Session rows include final
  totals and winner, so no separate results table is needed.
- The database stores private configuration/role assignments for research records;
  these are not exposed through participant endpoints.

Key files:

| Location | Responsibility |
| --- | --- |
| `backend/app/config.py` | Configuration validation |
| `backend/app/engine.py` | State machine, chat and voting rules, totals |
| `backend/app/main.py` | FastAPI lifecycle, routes, WebSocket schemas, static hosting |
| `backend/app/session.py` | Participant tokens, queues, broadcasts, persistence hooks |
| `backend/app/scripted_ai.py` | Predefined discussion messages and deterministic votes |
| `backend/app/storage.py`, `schema.sql` | PostgreSQL repository and schema |
| `frontend/src/App.jsx` | Join, Waiting Room, Discussion Chat, Voting, Final Results |
| `frontend/src/useExperiment.js`, `protocol.js` | Reconnects, protocol state, countdown |
| `compose.yml`, `Dockerfile`, `docker/start-postgres.sh` | Deployment and credential bootstrap |

## YAML configuration

The current `config.yml` contains:

```yaml
participants:
  humans: 1
  ai: 2
discussion_seconds: 60
voting_seconds: 30
```

Durations apply to each round and must be positive integers. There are always
exactly three players and exactly two rounds. Supported compositions:

| Humans | AI | Equivalent YAML role list |
| --- | --- | --- |
| 3 | 0 | `participants: [human, human, human]` |
| 2 | 1 | `participants: [human, human, ai]` |
| 1 | 2 | `participants: [human, ai, ai]` |

Use either the count mapping or the role list. List order does not assign public
labels; role-to-label assignments are shuffled separately. Configuration is loaded
server-side from a read-only mount. After editing it:

```sh
docker compose restart app
```

This starts a **new** session. For multiple human participants, use separate browser
profiles or browsers: tabs in the same profile share localStorage and the same
identity. Connecting the same token twice replaces the older connection.

## API and reconnects

| Endpoint | Purpose |
| --- | --- |
| `POST /join` or `POST /api/join` | Allocate a human slot; return label, private token, public state |
| `WS /ws` | Authenticate, chat, vote, receive real-time events |
| `GET /health` | Application/database readiness |
| `GET /docs` | HTTP API documentation |
| `GET /` | Built React frontend |

The first WebSocket frame is `{"type":"auth","token":"YOUR_TOKEN"}`. Actions:

```json
{"type":"chat","text":"I suggest Player B.","round":1}
{"type":"vote","target":"B","round":1}
```

`welcome` restores identity, recent chat and voted rounds. `state`, `chat`, and
`vote_received` update all connected clients; `error` goes only to the sender.
Ballot targets are not broadcast. Tokens stay out of URLs and public payloads.
Full schemas and console testing instructions: [backend/API.md](backend/API.md).

## Design decisions

- **Fixed server deadlines:** voting ends at its deadline even if all ballots arrive
  early. A missing vote is an abstention, so an absent player cannot stall a round.
- **One vote per player per round:** enforced by the engine and a database primary
  key. Self-votes are allowed. The UI locks a ballot after server acknowledgement.
- **Combined results:** totals include both rounds. Alphabetical order breaks ties;
  if no votes are cast, A wins the all-zero tie. This rule is deterministic but
  intentionally favors earlier labels when tied.
- **Scripted AI:** once per round, each AI nominates the next label cyclically
  (A to B, B to C, C to A), sends a short predefined message, and votes accordingly.
  This makes behavior reproducible and testable without network latency, API keys,
  external language models, or paid services. It is not adaptive conversation.
- **One active session/worker:** in-memory coordination keeps the assessment small.
  PostgreSQL retains records, while the engine remains the sole authority for rules.
- **Safe persistence:** parameterized queries and transactions prevent text from
  becoming SQL. A write failure stops new actions and makes health return 503;
  restart after fixing the database rather than continuing with divergent state.

## Persistence and known limitations

**Active sessions do not survive application restarts.** Every startup creates a new
session UUID and marks previous active sessions interrupted. Committed messages,
votes, and completed results survive in the PostgreSQL volume. Tokens, live timers,
and socket bindings do not. The UI offers to clear an expired identity and rejoin.

- One session per process, one worker, no automatic session reset after completion.
- No admin/export UI, schema migration framework, or full restart recovery.
- Synchronous database writes can delay the server loop; queries have a timeout.
  A scheduler stall can skip expired phases and their scripted actions.
- Only the most recent 100 messages are replayed on reconnect; all committed
  messages remain in PostgreSQL.
- No role fields reach clients, but scripted wording/timing can reveal behavioral
  cues. The implementation cannot guarantee that participants never infer roles.
- This is a local assessment prototype: no participant admission controls,
  rate limiting, TLS termination, or production access policy. Join is not
  idempotent; a lost join response can consume a slot without delivering its token.
- Dependencies/images are not all pinned to immutable digests. The frontend has
  a lockfile; Python transitive dependencies can change between installs.
- Docker cold startup and a visual browser walkthrough are still unverified.
  A previous backend run hit intermittent TestClient cancellation during reconnect
  cleanup; subsequent runs passed. HTTPX emits a non-failing deprecation warning.

`docker compose down` preserves data. **`docker compose down -v` deletes research
records and generated database credentials.** Keep the database and credential
volumes together. See [DEPLOYMENT.md](DEPLOYMENT.md) for details.

## Development and tests

For separate local FastAPI/Vite processes, see [frontend/README.md](frontend/README.md).
Without `DATABASE_URL` or `PGHOST`, the local backend runs in memory; Compose sets
the PostgreSQL connection variables automatically.

From the project root in PowerShell (Python installed):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd ../frontend
npm ci
npm test
npm run build
```

Use `npm.cmd` if PowerShell blocks `npm.ps1`. On macOS/Linux use `python3` and
`.venv/bin/python` paths. For real database tests, set `TEST_DATABASE_URL` to a
test database whose user can create schemas; tests isolate and remove their own
schemas. Do not point tests at participant data.

Verified evidence as of the submission review:

| Check | Result |
| --- | --- |
| Current backend suite | 23 passed, 2 PostgreSQL tests skipped (no test DB configured) |
| Prior PostgreSQL integration run | All 25 passed on a temporary PostgreSQL 18 cluster |
| Current frontend protocol tests | 4 passed |
| Current frontend production build | Passed with Vite 7.3.8 |
| Prior live HTTP/WebSocket proxy smoke test | Passed join, chat, voting, results and reconnect |
| Docker image/Compose startup | Not run; Docker unavailable |
| Browser visual/click-through verification | Not performed; browser access unavailable |

## Assessment and submission

[SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) maps requirements to source and
records remaining verification steps. [ai_prompts.md](ai_prompts.md) contains the
actual user prompts available in this conversation, tool provenance, and verified
activity. The exact model revision is not available in the record and is explicitly
marked unverified. No working application logic was changed during this review.
