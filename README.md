# Three-player group decision experiment

Core Python experiment engine for a Student Research Assistant technical
assessment at the Center for Humans and Machines. A minimal FastAPI HTTP/WebSocket
server now wraps the engine using in-memory storage and local scripted AI players.
Frontend, database, and Docker integration are not implemented yet. See
[server setup, protocol, and manual testing](backend/API.md).

## Proposed architecture

Use three Docker Compose services: a React frontend (Vite), a Python FastAPI
backend, and PostgreSQL. Compose will eventually build and start all three with
`docker compose up --build`. Compose files, dependencies, and runnable entry
points are deliberately deferred to the implementation stage.

- **React:** Render the waiting room, discussion, vote, and results views from
  server state. Send participant actions to the backend; display its deadlines.
- **FastAPI:** Own one session with three player slots. Use HTTP for joining and
  WebSockets for chat, actions, and authoritative state updates. A single session
  coordinator will advance waiting room → discussion 1 → vote 1 → discussion 2
  → vote 2 → final results. Enforce phase deadlines and action validity here.
- **PostgreSQL:** Persist sessions, player assignments, messages, votes, and round
  outcomes. Use a small SQLAlchemy persistence layer. Keep the initial schema
  simple; introduce migrations when schema evolution becomes necessary.
- **AI adapter:** Run inside the backend and submit actions through the same
  validation path as humans. Keep provider calls outside the coordinator and
  apply a timeout so a slow AI response cannot block phase transitions.
- **Configuration:** Load root `config.yml` on the backend only. At startup,
  validate integer counts totaling three, with one to three humans and zero to
  two AI players, plus positive phase durations. There are exactly two rounds.

## Participant identity

Give every participant one of the public labels A, B, and C.
Keep the human/AI assignment and join credentials private on the server. Use
explicit public response schemas so configuration, AI prompts, provider errors,
and player type never enter participant payloads. Render all players identically.
This hides system-provided identity cues; conversational behavior may still let
participants infer an AI's identity.

## Current structure

```text
backend/
  app/
    __init__.py
    config.py
    engine.py
    main.py
    session.py
    scripted_ai.py
  tests/
    test_engine.py
    test_api.py
    test_scripted_ai.py
  requirements.txt
  requirements-dev.txt
  API.md
frontend/
  src/
    .gitkeep
config.yml
.gitignore
ai_prompts.md
README.md
```

In later stages, add database models/access within
`backend/app/`. Add the React entry
point and views within `frontend/src/`. Add dependency manifests, Dockerfiles,
and Compose at that point. Avoid empty layers and abstractions until needed.

## Configuration examples

The default is three humans. Change only the participant counts for other modes:

| Mode | `participants.humans` | `participants.ai` |
| --- | --- | --- |
| All human | 3 | 0 |
| One AI | 2 | 1 |
| Two AI | 1 | 2 |

`discussion_seconds: 120` and `voting_seconds: 30` apply to each round.
Scripted AI requires no credentials.

## Scripted AI participants

The original count format remains supported. Alternatively, set `participants`
to any of these YAML lists (keep the duration fields unchanged):

```yaml
participants: [human, human, human]
# Or: participants: [human, human, ai]
# Or: participants: [human, ai, ai]
```

List order does not fix role-to-label assignment. The engine shuffles A, B, and C
at session creation, then privately reserves the required human and AI slots.
The last required human join immediately starts discussion; no AI connection or
join request is needed.

`ScriptedPlayers.step()` runs from the existing server ticker. Once per discussion
round, each AI nominates the next label cyclically (A nominates B, B nominates C,
C nominates A). It submits one vote for that same label in each voting round.
Round two uses a short follow-up message. Actions occur on the first scheduler
tick that observes the phase, normally within 250 ms. A private completed-action
set prevents repeat ticks from sending duplicate messages or votes.

Humans and AI share `SessionHub.submit_chat()` and `submit_vote()`, which call the
engine for validation and emit the same broadcast envelopes. Roles are never
added to public events, join responses, or history. The script cannot change
deadlines, and entirely missed phases are not replayed after a scheduler stall.

Scripted behavior was chosen for the time-limited assessment because it is easy
to explain, test, and reproduce, runs offline, and needs no credentials, external
LLM calls, paid services, or additional dependencies. For a fixed label assignment
its messages and votes are deterministic; only role assignment is randomized.
This is a functional simulation, not an adaptive conversational model. Repeated
wording and timing may let participants infer roles despite role-free payloads.

The full suite now contains 21 passing tests, including all three YAML role lists,
AI actions in both rounds, duplicate suppression, label shuffling, deterministic
behavior, expired-phase handling, and delivery through the in-process WebSocket
test client.

## Scope and trade-offs

- Target one three-player session per deployment and one backend worker for the
  two-hour build. In-memory coordination avoids Redis and distributed locking;
  multiple workers or concurrent sessions require additional coordination.
- Store research records in PostgreSQL, but defer automatic recovery of an
  interrupted session after a backend restart. Persistence alone does not provide
  timer or session recovery.
- Use server deadlines to avoid client clock authority. Participant reconnect
  remains deferred; missing votes and ties are handled as documented below.
- Use a Vite development server in the initial Compose setup for speed. Production
  hosting, authentication, and deployment hardening are outside this assessment.
- Keep AI behind a small adapter so provider choice can change without rewriting
  session logic. Identity masking cannot guarantee that humans never guess which
  players are AI.

## Engine API

Use Python 3.10 or newer. `load_config(path)` in `app.config` reads and validates
the server-only YAML into an immutable `ExperimentConfig`. Construct
`ExperimentSession(config)` from `app.engine` for each session.

| Method | Purpose |
| --- | --- |
| `join_human()` | Allocate and return a human's label; the last required human starts round 1. Reject joins after startup. |
| `ai_labels()` | Server-only assignments for a future AI adapter. Never expose these to clients. |
| `tick()` | Advance every expired phase using the server's monotonic clock. |
| `cast_vote(voter, target, round_number=...)` | Accept a valid vote, or raise `ExperimentError`. The round argument prevents stale votes being accepted in round 2. |
| `public_state()` | Return a fresh dictionary with labels, phase, round, seconds remaining, and final results. No roles, joined-label lists, or configuration. |

The waiting room has round 0 and no deadline. AI slots are reserved at creation;
only humans need to join. Roles are randomly assigned to labels so A, B, or C
does not consistently mean human or AI. Do not serialize the session/config
objects; use only `public_state()` as the shared client payload.

The engine is synchronous and has no background thread. The FastAPI server scheduler
calls `tick()` regularly, even when clients send no actions, and serializes
all operations on a session. This is the integration contract for automatic
deadline progression. Reads and votes also process elapsed deadlines. The clock
can be injected for deterministic tests, but must never come from client input.
The public countdown is informational; only the server's internal deadline
controls transitions. Delayed ticks catch up against the original schedule.

Each player may cast at most one vote in each round, for A, B, or C, including
themselves. A missing vote is an abstention, so voting does not block completion.
Voting always lasts its configured duration, even if all three votes arrive
early. Actions at the exact deadline are processed in the next phase. Results
remain hidden until both rounds finish.

Final totals sum both rounds. **Ties are resolved alphabetically by label** to
make the result deterministic without a third round. This favors earlier labels
in a tie; if nobody votes, all totals are zero and A wins by the same rule.

The transport binds each human connection to its allocated label using a private
token and derives `voter` from that binding. The core engine validates labels and
phases, but does not implement authentication. `join_human()` allocates a new slot
per call; the transport reconnects with the existing token instead of joining again.
The engine also exposes `post_chat()` for discussion/round/text validation,
`chat_history()` for the last 100 messages, and `voted_rounds(player)` for private
reconnect status.

## Running the unit tests

From the project root in PowerShell (with Python installed/on PATH):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On macOS/Linux, use `python3 -m venv .venv`, install with
`.venv/bin/python -m pip install -r backend/requirements-dev.txt`, then run
`../.venv/bin/python -m unittest discover -s tests -v` from `backend/`.

Tests use the standard-library `unittest` runner, a fake clock, and FastAPI's
in-process TestClient. No external services or database are needed.
