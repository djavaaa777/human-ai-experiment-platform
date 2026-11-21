# Human-AI Experiment Platform

A three-player group decision experiment built for a technical assessment. Players
discuss who should become the Decision Maker, then vote after each of two discussion
rounds. The same application supports human and scripted-AI participants.

## Technology

- React 19 and plain CSS; Vite for the frontend build.
- Python 3.12, FastAPI, Pydantic, and Uvicorn.
- PostgreSQL 17 with Psycopg 3.
- Docker Compose; YAML experiment settings in `config.yml`.

## Architecture

```text
Browser (React) -- HTTP join / WebSocket --> FastAPI
                                             |-- Experiment engine and session hub
                                             |-- PostgreSQL persistence
                                             `-- Serves the built React files
```

The engine owns the experiment phases and voting rules. The session hub connects
the engine to participants, scripted players, WebSocket broadcasts, and storage.
Compose runs only the app and database services; the app serves the frontend on
the same origin.

## Start the application

With Docker Desktop running, from the repository root:

```sh
docker compose up --build
```

Open [http://localhost:8081](http://localhost:8081). The current configuration is
one human and two scripted AI players, so a solo participant can start the
experiment. PostgreSQL data is kept in a named volume. `docker compose down`
stops the services without removing it; `docker compose down -v` removes the
database and generated credential volumes.

## Experiment configuration

Edit `participants` in the root `config.yml`. The values must total three, with at
least one human. For example:

```yaml
participants:
  humans: 3
  ai: 0
discussion_seconds: 60
voting_seconds: 30
```

Use `humans: 2, ai: 1` for two humans and one AI, or `humans: 1, ai: 2` for one
human and two AIs. The durations apply to each discussion and voting phase. The
server also accepts a three-item role list (`[human, human, ai]`) in place of the
human/AI counts. Restart the app to load changes:

```sh
docker compose restart app
```

This creates a new experiment session. In modes with multiple humans, use separate
browser profiles for separate participants; tabs in one profile share an identity.

## Experiment flow

Human participants join under shuffled labels A, B, or C. The experiment starts
when all configured human slots are filled. Players alternate between discussion
and voting for two rounds, then see combined vote totals and the selected Decision
Maker. The server controls phase timing and validates chat and ballots. Public
participant messages do not include human/AI roles or vote targets.

Scripted players send predefined discussion messages and vote deterministically;
they do not use an external language model. Their behavior can still make their
roles inferable.

## Design decisions and limitations

- The server is authoritative for state transitions, deadlines, and accepted
  actions. Voting remains open until its deadline; missing ballots are abstentions.
- Results count votes from both rounds. Alphabetical player-label order breaks
  ties, including an all-zero tie.
- A small, single-process session model keeps coordination simple. PostgreSQL
  preserves committed messages, votes, and results, but active sessions, timers,
  and reconnect tokens do not survive an app restart.
- The prototype has one active session and one app worker. Scripted AI is
  deterministic rather than conversational; role inference cannot be prevented.
- This is a local assessment application, not a production deployment. It does not
  provide participant admission controls or a production access policy.

For the API protocol, see [backend/API.md](backend/API.md). For local frontend
development, see [frontend/README.md](frontend/README.md). The complete AI-use
record, including the available prompts and verification history, is in
[ai_prompts.md](ai_prompts.md).
