# AI interaction log

This log covers the seven user task prompts available in the development
conversation, including the submission review. Full prompt text follows the
activity summaries; line-break escapes and HTML whitespace from the chat export
are normalized for readability, without paraphrasing the requests. IDE context,
tool output, and service-generated environment messages are not user prompts.
No interactions outside this conversation can be verified from this record.

## Model and tool provenance

- Development assistant/interface: **Codex**.
- **Exact model identifier/revision: not exposed in the available conversation
  record and not independently verified.** No specific model name is inferred.
  If the submission requires it, the author must supply a contemporaneous model
  selection record/export; otherwise retain this explicit limitation.
- Tools actually called: `functions.exec` orchestrating `exec_command`,
  `apply_patch`, `write_stdin`, and `web__run`; `mcp__cua_repl.js` for browser
  availability discovery during stage 5. The browser host was unavailable; no
  successful browser interaction or visual inspection followed.
- Local programs actually used: PowerShell, Git (read-only checks by the assistant),
  Python/venv/pip, unittest, PostgreSQL initdb/pg_ctl and Psycopg, Node/npm/Vite.
  HTTP/WebSocket smoke checks used HTTPX and the websockets client.
- Skill used: Sites, local-only workflow, including its dependency-install helper.
  The Computer Use skill was read, but no native Windows UI was controlled.
- Web tool use: official FastAPI, Vite, Psycopg, and Docker documentation lookups.
- No delegated agents, external runtime LLM API calls, image generation, or paid
  AI services were used for the experiment. Docker commands were documented but
  could not be executed because Docker was unavailable.
- Existing Git commits were observed during review. Their creation is not an
  assistant activity in this conversation; no commit or push tool call was made.

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
  Initial communication tests failed with a 10 ms test ticker and passed after
  changing the test interval to 100 ms (production uses 250 ms). The exact cause
  of the original failures was not established. All 17 engine and
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

### Stage 7 - Submission review

- Tool: Codex; exact model revision unverified as explained above.
- Request: Review the completed project, finalize documentation, audit actual
  AI interactions and Git hygiene, and provide a submission checklist without
  application-logic changes, commits, or pushes.
- Work: Rewrote README to reflect the actual implementation/current demo config;
  added full available user prompts and provenance limitations to this log;
  created a requirement matrix, findings, and submission checklist.
- Verification this stage: backend suite 23 passed and 2 database tests skipped;
  frontend 4 tests passed; production build passed. Read-only Git checks covered
  36 tracked files and six reachable commits. No generated directories or sensitive
  filename candidates were tracked, and no matches were found for the selected
  private-key/API-key/credential-URL patterns. This is not a comprehensive secret
  scan guarantee. Ignore rules for `.env`, `.venv`, node_modules, dist and Python
  caches were confirmed. The existing modified config.yml was preserved.
- Limitations: no Docker startup or browser walkthrough performed; the prior real
  PostgreSQL test run is historical evidence, not a database rerun in this stage.
- Human review: Pending. No application logic changes, commits, or pushes.

## Actual user prompts

### Prompt 1 - Architecture and scaffold

```text
I am building a technical assessment for a Student Research Assistant – Full-Stack Developer position at the Center for Humans and Machines.

The task is to build a minimal real-time group decision-making experiment with 3 participants.

Requirements:
- React frontend
- Python FastAPI backend
- PostgreSQL database
- Docker Compose for one-command startup
- YAML configuration for 3 humans, 2 humans + 1 AI, or 1 human + 2 AI agents
- Waiting room, 2 discussion rounds, voting after each round, and final results
- Participants must not know which players are humans or AI

We have approximately 2 hours for implementation. Optimize for clean architecture and working functionality, not visual polish.

For this first stage ONLY:
1. Propose the simplest architecture and explain the components.
2. Initialize a minimal backend/frontend folder structure.
3. Create config.yml with participants, discussion_seconds, and voting_seconds.
4. Create an appropriate .gitignore.
5. Create ai_prompts.md with a section for recording our AI interactions.
6. Explain the choices and trade-offs.

Do not implement the experiment logic yet. Do not create Git commits or push anything. Do not claim anything was tested unless it was actually run. Stop after this stage so I can inspect the structure.
```

### Prompt 2 - Experiment engine

```text
Continue with the existing project. Implement ONLY the core experiment engine in Python.

Requirements:
1. Each session has exactly 3 anonymous players: A, B and C.
2. Player roles come from config.yml and must remain hidden from clients.
3. Human participants wait until all human slots are filled.
4. There are 2 discussion rounds, each followed by a voting phase.
5. Each participant can vote exactly once per round.
6. Players may vote for any of the three participants.
7. The server controls all phase transitions and deadlines.
8. If the voting deadline expires, automatically move forward.
9. Final results count votes from both rounds; ties are resolved alphabetically by player label. Document this design choice.

Use a simple state-machine design, separate from HTTP routes and database implementation.

Create focused unit tests for:
- Waiting room behavior
- Round transitions
- Duplicate vote rejection
- Final winner calculation

Do not implement React, WebSockets, database integration, or Docker in this stage.

Explain the public methods and tell me how to run the tests. Do not commit changes. Stop after implementation.
```

### Prompt 3 - FastAPI and WebSockets

```text
Continue the project using the existing experiment engine.

Implement a minimal FastAPI server with real-time communication.

Requirements:
1. A participant can join an experiment and receive a unique player identity and private reconnect token.
2. Use WebSockets for real-time chat messages, voting events, phase updates and countdown synchronization.
3. Broadcast messages and state changes to all participants in the same session.
4. Validate messages and votes on the server.
5. Never expose whether another participant is human or AI.
6. Allow a participant to reconnect using their private token.
7. Keep the implementation simple. One active session at a time is acceptable for this assessment.
8. Keep business logic in the experiment engine instead of duplicating it in API routes.

For now, use in-memory session storage. PostgreSQL integration comes later.

Do not implement the frontend or AI agents yet.

Explain the API endpoints, WebSocket message format, and how I can manually test two participants.

Do not create commits. Stop when the server-side communication layer is ready.
```

### Prompt 4 - Scripted AI

```text
Continue with the current FastAPI experiment platform.

Implement minimal scripted AI participants.

Requirements:
1. Support all three YAML configurations:
   [human, human, human]
   [human, human, ai]
   [human, ai, ai]
2. Shuffle the player labels A, B and C when creating a session.
3. AI agents must participate in discussions by sending short, relevant predefined messages.
4. AI agents must submit valid votes automatically.
5. AI messages must use the same event and broadcast mechanism as human messages.
6. Never reveal human/AI roles through public WebSocket messages or API responses.
7. Start the experiment as soon as the required human participants have joined.
8. Do not use external LLM APIs, API keys, or additional paid services.

Write tests verifying that all three configurations work and that AI participants can send messages and vote.

Keep the implementation deterministic and simple enough to explain in an interview.

Document why scripted AI behavior was chosen instead of a real language model.

Do not modify unrelated files or create Git commits.
```

### Prompt 5 - React frontend

```text
Continue with the existing FastAPI backend and WebSocket protocol.

Build a minimal React frontend with Vite.

Implement these screens:
1. Join Experiment
2. Waiting Room
3. Discussion Chat
4. Voting
5. Final Results

Functional requirements:
- Connect to the existing backend using its actual API and WebSocket message format.
- Display the current player name (Player A, B or C).
- Display messages from all participants in real time.
- Show a countdown based on server-provided deadlines.
- Allow sending chat messages during discussion only.
- Allow one vote per participant during each voting phase.
- Show final vote totals and the selected Decision Maker.
- Preserve the reconnect token in localStorage for page refreshes.
- Never display which participants are AI.

Use basic responsive CSS with clean, readable styling.
Do not use heavy component libraries or spend time on animations.

Do not rewrite the backend unless an integration issue requires a small fix. Explain any such fix.

Tell me how to run the frontend and backend locally.

Do not create commits. Stop after this stage.
```

### Prompt 6 - PostgreSQL and Docker

```text
Continue the existing React + FastAPI experiment platform.

Add PostgreSQL persistence and Docker Compose support.

Requirements:
1. Store experiment sessions, discussion messages, votes and final results in PostgreSQL.
2. Keep the database schema minimal.
3. Use parameterized database queries or a suitable safe database library.
4. Use Docker Compose to run PostgreSQL and the application.
5. Build the React frontend and serve its static files through FastAPI to simplify local deployment.
6. The complete application must start with:
   docker compose up --build
7. Expose the application on host port 8081 because port 8080 may be unavailable on my Windows computer.
8. Load experiment parameters from config.yml.
9. Do not hardcode real credentials or commit secrets.
10. Clearly document whether active sessions survive an application restart. If full session recovery is too complex, prioritize persistent messages, votes and results, and explain the limitation.

Keep the Docker setup minimal and avoid unnecessary services.

Do not rewrite working experiment logic or create Git commits.

Explain how to verify database connectivity and application startup.
```

### Prompt 7 - Submission review

```text
Review the completed Human-AI Experiment Platform project and prepare it for submission to the Max Planck Institute.

1. Finalize README.md with project overview, architecture, technology stack, Docker startup instructions, YAML configuration, design decisions and known limitations.
2. Review ai_prompts.md and ensure it contains all actual AI prompts, exact models/tools used, and verified development activities. Do not invent any interactions.
3. Check whether the source code, config.yml, Docker setup and documentation meet the technical assessment requirements.
4. Check that no sensitive credentials or unnecessary generated files are tracked by Git.
5. Provide a final submission checklist.

Do not change working application logic.
Do not create commits or push changes.
Explain any problems you identify.
```

## Experiment agent prompts

No language-model prompts are used. `backend/app/scripted_ai.py` contains two
predefined discussion templates and a cyclic label-based voting rule. See the
README's scripted AI section for behavior and rationale.
