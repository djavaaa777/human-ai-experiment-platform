# Three-player group decision experiment

Stage 1 scaffold for a Student Research Assistant technical assessment at the
Center for Humans and Machines. No experiment logic is implemented yet.

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

Give every participant the same kind of public label, such as Player 1–3.
Keep the human/AI assignment and join credentials private on the server. Use
explicit public response schemas so configuration, AI prompts, provider errors,
and player type never enter participant payloads. Render all players identically.
This hides system-provided identity cues; conversational behavior may still let
participants infer an AI's identity.

## Initial structure

```text
backend/
  app/
    __init__.py
frontend/
  src/
    .gitkeep
config.yml
.gitignore
ai_prompts.md
README.md
```

In the implementation stage, add the FastAPI entry point, session coordinator,
database models/access, and AI adapter within `backend/app/`. Add the React entry
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
AI credentials will come from environment variables, never this YAML file.

## Scope and trade-offs

- Target one three-player session per deployment and one backend worker for the
  two-hour build. In-memory coordination avoids Redis and distributed locking;
  multiple workers or concurrent sessions require additional coordination.
- Store research records in PostgreSQL, but defer automatic recovery of an
  interrupted session after a backend restart. Persistence alone does not provide
  timer or session recovery.
- Use server deadlines to avoid client clock authority. Participant reconnect,
  missing-vote handling, and tie rules need explicit behavior in the next stage.
- Use a Vite development server in the initial Compose setup for speed. Production
  hosting, authentication, and deployment hardening are outside this assessment.
- Keep AI behind a small adapter so provider choice can change without rewriting
  session logic. Identity masking cannot guarantee that humans never guess which
  players are AI.

## Current verification status

No application tests, builds, or Docker startup have been run. This stage contains
only a scaffold, configuration, and documentation; it is not runnable yet.
