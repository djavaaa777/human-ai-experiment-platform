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

## Template for subsequent interactions

### Stage / topic

- Tool / model:
- Prompt or faithful summary:
- Relevant response / suggested changes:
- Changes accepted or rejected, and why:
- Human review and verification actually performed:

## Experiment agent prompts

Not implemented yet. Record the AI players' runtime instructions here when they
are introduced; keep those separate from this development assistance log.
