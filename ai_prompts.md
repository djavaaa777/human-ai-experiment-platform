# AI interaction log

This log covers the eight user task prompts available in the development
conversation, including this final cleanup request. Full prompt text follows the
activity summaries; line-break escapes and HTML whitespace from the chat export
are normalized for readability, without paraphrasing the requests. IDE context,
tool output, and service-generated environment messages are not user prompts.
No interactions outside this conversation can be verified from this record.

## Model and tool provenance

- Development assistant/interface recorded for stages 1–7: **Codex**. The final
  cleanup stage used the **Copilot SDK in VS Code**.
- **Exact model identifier/revision: not exposed in the available conversation
  record and not independently verified.** No specific model name is inferred.
  If the submission requires it, the author must supply a contemporaneous model
  selection record/export; otherwise retain this explicit limitation.
- Tools recorded for stages 1–7: `functions.exec` orchestrating `exec_command`,
  `apply_patch`, `write_stdin`, and `web__run`; `mcp__cua_repl.js` for browser
  availability discovery during stage 5. The development assistant's browser
  host was unavailable then. For the final cleanup, repository files were
  inspected with `functions.view`, `functions.rg`, and `functions.glob`, edited
  with `functions.apply_patch`, and checked with `functions.powershell` and
  `multi_tool_use.parallel`.
- Local programs actually used: PowerShell, Git (read-only checks by the assistant),
  Python/venv/pip, unittest, PostgreSQL initdb/pg_ctl and Psycopg, Node/npm/Vite.
  HTTP/WebSocket smoke checks used HTTPX and the websockets client.
- Skill used: Sites, local-only workflow, including its dependency-install helper.
  The Computer Use skill was read, but no native Windows UI was controlled.
- Web tool use: official FastAPI, Vite, Psycopg, and Docker documentation lookups.
- No delegated agents, external runtime LLM API calls, image generation, or paid
  AI services were used for the experiment. The development assistant could not
  run Docker in its environment; the author later ran the application with Docker.
- Existing Git commits were observed during review. Their creation is not an
  assistant activity in this conversation; no commit or push tool call was made.

## Confirmed human contribution

The author reports starting the application locally with Docker and manually
testing the experiment in a browser. The walkthrough covered participant joining,
real-time communication, voting, both discussion rounds, and final results. The
author also reviewed the completed behavior before preparing the submission.
This confirms the main workflow only; it does not mean every feature, AI-assisted
change, configuration, browser, viewport, or edge case was individually tested.
No stage-by-stage human review beyond this completed-behavior review is claimed.

## Recorded interactions

### Stage 1 — Architecture and scaffold

- Tool: Codex
- Request summary: Propose a minimal React/FastAPI/PostgreSQL architecture for a
  three-player experiment, scaffold folders, add YAML configuration and ignores,
  and explain trade-offs. Do not implement experiment logic, commit, or push.
- Assistance: Proposed one backend-owned session state machine, WebSocket updates,
  PostgreSQL persistence, and server-side AI adapters. Created the initial folder
  structure, configuration, and documentation.
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
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
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
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
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
- Verification: Installed declared server/test dependencies in the local venv.
  Initial communication tests failed with a 10 ms test ticker and passed after
  changing the test interval to 100 ms (production uses 250 ms). The exact cause
  of the original failures was not established. All 17 engine and
  in-process API tests passed. TestClient reports a non-failing HTTPX deprecation
  warning. The author later performed the overall browser walkthrough described
  above; no separate stage-specific review is recorded.

### Stage 4 — Local scripted AI participants

- Tool: Codex
- Request summary: Support three human/AI compositions, shuffled labels, scripted
  discussion messages and automatic valid votes, shared broadcasts, hidden roles,
  and tests, without external LLM services or commits.
- Assistance: Added deterministic per-label scripted behavior driven by the
  existing ticker, shared human/AI submission methods, and YAML role-list support
  alongside the existing count format. Kept the engine's existing label shuffle.
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
- Verification: Ran the full unittest suite: all 21 tests passed, including four
  new tests covering compositions, AI actions, determinism/shuffling, delayed
  ticks, and WebSocket delivery. The existing non-failing HTTPX deprecation warning
  remains. The author later performed the overall browser walkthrough described
  above; no separate stage-specific review is recorded.

### Stage 5 — React/Vite frontend

- Tool: Codex
- Request summary: Build five minimal responsive screens using the existing HTTP
  and WebSocket protocol, show messages/countdowns/votes/results, persist reconnect
  tokens in localStorage, and keep roles hidden. No commits.
- Assistance: Added React views, socket/reconnect handling, pure event-state helpers,
  responsive CSS, Vite HTTP/WebSocket proxies, dependency lockfile, tests, and local
  run instructions. Used the Sites skill's local-only workflow; no publication.
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
- Verification: Four frontend protocol tests and the production build passed.
  A local HTTP/WebSocket smoke test through Vite to FastAPI passed join, waiting,
  chat, voting, final results, and reconnect checks. All 21 backend tests passed
  on rerun after an intermittent TestClient cancellation in reconnect cleanup.
  Browser automation was unavailable, so no visual/click-through verification
  was performed by the development assistant at that stage. The author later
  performed the overall browser walkthrough described above; no separate
  stage-specific review is recorded. No backend source changes were required.

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
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above.
- Verification: All 25 backend tests passed against an isolated PostgreSQL 18
  cluster, including real persistence, transaction rollback, final results, and
  restart behavior. Static routing and persistence failure behavior were tested.
  Compose YAML parsed and service/port checks passed. The development assistant
  could not run the Docker image or Compose startup in its environment; the author
  later ran the app with Docker, as described above. The temporary cluster was
  stopped and removed. The existing HTTPX deprecation warning remains non-failing.

### Stage 7 - Submission review

- Tool: Codex; exact model revision unverified as explained above.
- Request: Review the completed project, finalize documentation, audit actual
  AI interactions and Git hygiene, and provide a submission checklist without
  application-logic changes, commits, or pushes.
- Work: Rewrote README to reflect the implementation/current demo config; added
  the prompts and provenance limitations to this log; reviewed requirements and
  repository hygiene.
- Verification this stage: backend suite 23 passed and 2 database tests skipped;
  frontend 4 tests passed; production build passed. Read-only Git checks covered
  36 tracked files and six reachable commits. No generated directories or sensitive
  filename candidates were tracked, and no matches were found for the selected
  private-key/API-key/credential-URL patterns. This is not a comprehensive secret
  scan guarantee. Ignore rules for `.env`, `.venv`, node_modules, dist and Python
  caches were confirmed. The existing modified config.yml was preserved.
- Limitations: the assistant did not run Docker or a browser in that review; the
  prior real PostgreSQL test run is historical evidence, not a database rerun in
  that stage. The author subsequently confirmed the Docker/browser checks above.
- Human review at this stage: Not documented in the available history; see the
  confirmed overall review above. No application logic changes, commits, or pushes.

### Stage 8 - Final cleanup

- Tool: Copilot SDK in VS Code; exact model identifier unverified.
- Request: Shorten the README, remove redundant documentation, preserve all prompts,
  accurately record AI and human work, review technical requirements and secrets,
  correct the database healthcheck if appropriate, and run final checks without
  changing application logic or Git history.
- Work: Rewrote the README, retained the API and local-development guides, removed
  the redundant deployment guide and checklist, updated stale documentation,
  and changed the PostgreSQL healthcheck to probe TCP on loopback.
- Human contribution: The confirmed Docker startup and browser walkthrough are
  documented above. No new human coding activity is claimed.
- Validation: Backend suite: 25 tests ran, 23 passed, and 2 PostgreSQL tests were
  skipped because `TEST_DATABASE_URL` was unset; the TestClient HTTPX deprecation
  warning remains non-failing. Frontend: 4 tests and the Vite production build
  passed.
  `docker compose config` parsed successfully and rendered the PostgreSQL TCP
  healthcheck. `git diff --check` passed; README length is 96 lines. The tracked
  secret-pattern scan and stale-document-link check are recorded after execution.
  The Docker image was not started during this cleanup; the author's prior local
  Docker startup and browser walkthrough are described above. No commits or pushes
  were made.

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

### Prompt 8 - Final cleanup

```text
We have completed the Human-AI Experiment Platform technical assessment for the Center for Humans and Machines at the Max Planck Institute for Human Development.

I want you to perform a final cleanup of the repository and its documentation before submission.

IMPORTANT CONTEXT:
- The project was developed with AI assistance under a strict 4-hour maximum time budget.
- I personally ran the application locally using Docker.
- I manually tested the main experiment workflow in the browser, including participant joining, real-time chat, voting, two discussion rounds, and final results.
- I reviewed the behavior of the application and checked that the core functionality worked.
- Do not generalize this into a claim that every feature or every AI-generated change was individually tested unless there is evidence.
- The goal is an honest, concise, professional technical-assessment submission.

TASK 1 — SIMPLIFY THE README

Rewrite README.md to be substantially shorter, ideally around 80–120 lines.

Keep only:
1. A brief project description.
2. Technology stack.
3. Simple architecture overview.
4. How to start the application with docker compose up --build.
5. How to switch between the three human/AI configurations in config.yml.
6. Brief explanation of the experiment flow.
7. Important design decisions and trade-offs.
8. A short known-limitations section.

Avoid long API documentation, repeated explanations, excessive tables, unnecessary implementation details and marketing-style wording.

Keep the README technical, clear and natural, as if written by a student developer explaining a focused project.

Ensure that every command, feature and configuration example matches the actual implementation.

TASK 2 — REMOVE REDUNDANT DOCUMENTATION

Review DEPLOYMENT.md, SUBMISSION_CHECKLIST.md and any other auxiliary documentation.

Remove redundant files if their essential information is already included in README.md, but preserve any documentation necessary to run, understand or evaluate the project.

If removing files, also remove broken references to them.

Do NOT delete ai_prompts.md, source code, tests, configuration or Docker-related files.

TASK 3 — IMPROVE THE AI USAGE LOG

Keep ai_prompts.md because the assessment explicitly requires a complete AI usage record.

Preserve ALL actual prompts in full, in chronological order. Do not summarize or delete prompts simply to shorten the file.

Include:
- The actual AI tools used during development.
- Exact model names where verifiable.
- The purpose of each development stage.
- A concise description of what the AI contributed.
- A concise description of what I personally reviewed, tested or decided.
- The actual validation steps and their outcomes.

Where appropriate, distinguish between AI-assisted implementation and human verification.

For the human contribution section, reflect the following confirmed activities:
- I started the application locally with Docker.
- I tested the experiment manually in the browser.
- I checked participant joining, real-time communication, voting, both discussion rounds and final results.
- I reviewed the completed behavior before preparing the submission.

Do not automatically claim that all stages were individually tested immediately after each prompt. Only document stage-specific reviews or tests that I actually performed or that the available records support.

Remove outdated statements that manual browser testing or Docker startup were never performed, but retain any genuine limitations regarding automated tests or unverified scenarios.

If the model identifier cannot be verified, clearly mark it as unverified rather than guessing.

Keep the AI log factual and transparent. Do not conceal substantial AI assistance or invent human coding activities.

TASK 4 — FINAL TECHNICAL REVIEW

Without rewriting the application, check:
- All technical-assessment requirements are represented.
- No hardcoded secrets are tracked.
- The Docker startup command is correct.
- The PostgreSQL configuration matches the application.
- The three YAML configurations are supported.
- Anonymous player identities remain hidden.
- Two rounds, voting and final results are implemented.
- README statements match the code.

Review the PostgreSQL healthcheck. If changing it to a TCP check using pg_isready -h 127.0.0.1 is appropriate, explain the reason before applying the change, and verify the Compose configuration afterward.

Avoid unrelated changes or new features.

TASK 5 — FINAL VALIDATION AND REPORT

Run available documentation/configuration checks and automated tests where possible.

Do not claim success for tests that could not be executed.

When finished, provide:
1. List of modified files.
2. List of deleted files, if any.
3. Short summary of changes.
4. Tests or checks actually executed and their results.
5. Remaining issues, if any.

STYLE REQUIREMENTS:
- Concise and professional.
- Natural English.
- No exaggerated claims.
- No unnecessary explanations.
- No invented development history.
- No redundant documentation.
- Honest about AI involvement and actual human contribution.

IMPORTANT:
Do not rewrite working application logic.
Do not remove required assessment materials.
Do not modify Git history.
Do not create commits or push to GitHub.

Make the repository clean, minimal and ready for final human review before submission.
```

## Experiment agent prompts

No language-model prompts are used. `backend/app/scripted_ai.py` contains two
predefined discussion templates and a cyclic label-based voting rule. See the
README's experiment-flow section for behavior and rationale.
