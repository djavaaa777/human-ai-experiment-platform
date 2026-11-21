# AI interaction log

Record material AI assistance here as development proceeds. Do not include API
keys, participant data, or other secrets.

## Recorded interactions

### Stage 1 — Architecture and scaffold

- Tool: Codex
- Request summary: Propose a minimal React/FastAPI/PostgreSQL architecture for a
  three-player experiment, scaffold folders, add YAML configuration and ignores,
  and explain trade-offs. Do not implement experiment logic, commit, or push.
- Assistance: Proposed one backend-owned session state machine, WebSocket updates,
  PostgreSQL persistence, and server-side AI adapters. Created the initial folder
  structure, configuration, and documentation.
- Human review: Pending.
- Validation: No application tests run; no runnable application exists at this stage.

### Stage 2 — Standalone experiment engine

- Tool: Codex
- Request summary: Implement only a Python state machine for three anonymous
  players, YAML-derived private roles, a human waiting room, two timed discussion
  and voting rounds, one vote per player per round, and combined final results
  with alphabetical tie-breaking. Add focused unit tests; no integrations or commits.
- Assistance: Added validated configuration loading, randomized private role
  assignments, a synchronous engine with injectable server clock, public snapshots,
  and 11 unit tests. Documented fixed voting windows, abstentions, alphabetical
  ties (including an all-zero result), and the future server tick-loop contract.
- Human review: Pending.
- Verification: The first test commands encountered a discovery-path error and
  then missing PyYAML. Created a local ignored virtual environment and installed
  the declared dependency. Ran `..\.venv\Scripts\python.exe -m unittest discover
  -s tests -v` from `backend/`: all 11 tests passed. No frontend, database,
  WebSocket, or Docker tests were run.

### Stage 3 — In-memory FastAPI communication

- Tool: Codex
- Request summary: Add private participant identities and reconnect tokens,
  WebSocket chat/voting/state/countdowns, server validation, broadcasts, and
  reconnect support around the existing engine. No frontend, AI, database, or commits.
- Assistance: Added a FastAPI lifespan ticker, an in-memory identity/delivery hub,
  strict message schemas, bounded per-connection queues, and reconnect snapshots.
  Extended the engine with chat validation/history and private voting status.
  Documented endpoints, wire messages, and a two-tab manual walkthrough.
- Human review: Pending.
- Verification: Installed declared server/test dependencies in the local venv.
  Initial communication tests failed with an overly aggressive 10 ms test ticker;
  changed the test interval to 100 ms (production uses 250 ms). All 17 engine and
  in-process API tests passed. TestClient reports a non-failing HTTPX deprecation
  warning. No live browser/network walkthrough was run.

### Stage 4 — Local scripted AI participants

- Tool: Codex
- Request summary: Support three human/AI compositions, shuffled labels, scripted
  discussion messages and automatic valid votes, shared broadcasts, hidden roles,
  and tests, without external LLM services or commits.
- Assistance: Added deterministic per-label scripted behavior driven by the
  existing ticker, shared human/AI submission methods, and YAML role-list support
  alongside the existing count format. Kept the engine's existing label shuffle.
- Human review: Pending.
- Verification: Ran the full unittest suite: all 21 tests passed, including four
  new tests covering compositions, AI actions, determinism/shuffling, delayed
  ticks, and WebSocket delivery. The existing non-failing HTTPX deprecation warning
  remains. No live browser walkthrough was run.

### Stage 5 — React/Vite frontend

- Tool: Codex
- Request summary: Build five minimal responsive screens using the existing HTTP
  and WebSocket protocol, show messages/countdowns/votes/results, persist reconnect
  tokens in localStorage, and keep roles hidden. No commits.
- Assistance: Added React views, socket/reconnect handling, pure event-state helpers,
  responsive CSS, Vite HTTP/WebSocket proxies, dependency lockfile, tests, and local
  run instructions. Used the Sites skill's local-only workflow; no publication.
- Human review: Pending.
- Verification: Four frontend protocol tests and the production build passed.
  A local HTTP/WebSocket smoke test through Vite to FastAPI passed join, waiting,
  chat, voting, final results, and reconnect checks. All 21 backend tests passed
  on rerun after an intermittent TestClient cancellation in reconnect cleanup.
  Browser automation was unavailable, so no visual/click-through verification
  was performed. No backend source changes were required.

### Stage 6 — PostgreSQL persistence and Docker Compose

- Tool: Codex
- Request summary: Persist sessions, chat, votes and results; package the React
  build with FastAPI; add two-service Compose on host port 8081; keep configuration
  in YAML and credentials out of source; explain restart limitations. No commits.
- Assistance: Added a three-table schema and parameterized Psycopg repository,
  commit-before-broadcast integration, fail-closed write behavior, static serving,
  and `/api/join` alias. Added a multi-stage Dockerfile, Compose healthchecks,
  generated password volume, and deployment/verification documentation.
- Design limitation: Application restarts create a new session. Existing records
  persist and prior active sessions are marked interrupted; tokens/timers are not
  restored. The experiment engine itself was unchanged.
- Human review: Pending.
- Verification: All 25 backend tests passed against an isolated PostgreSQL 18
  cluster, including real persistence, transaction rollback, final results, and
  restart behavior. Static routing and persistence failure behavior were tested.
  Compose YAML parsed and service/port checks passed. Docker is unavailable here,
  so image build and Compose startup were not run. The temporary cluster was
  stopped and removed. The existing HTTPX deprecation warning remains non-failing.

## Template for subsequent interactions

### Stage / topic

- Tool / model:
- Prompt or faithful summary:
- Relevant response / suggested changes:
- Changes accepted or rejected, and why:
- Human review and verification actually performed:

## Experiment agent prompts

No language-model prompts are used. `backend/app/scripted_ai.py` contains two
predefined discussion templates and a cyclic label-based voting rule. See the
README's scripted AI section for behavior and rationale.
