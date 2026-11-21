# Submission review and checklist

Review date: 21 November 2026. Scope: the assessment requirements supplied in this
conversation; no separate institute rubric or submission portal instructions were
provided. Documentation was updated; application logic and the author's existing
config.yml change were preserved. No commits or pushes were made by the assistant.

## Requirement coverage

| Requirement | Evidence | Assessment |
| --- | --- | --- |
| React frontend, five screens, responsive CSS | `frontend/src/App.jsx`, `styles.css` | Implemented; build passed; visual walkthrough pending |
| Python FastAPI and WebSockets | `backend/app/main.py`, `session.py` | Implemented; API tests and prior network smoke check passed |
| Three anonymous players and shuffled role assignments | `engine.py`, `config.py` | Covered by engine/scripted-player tests |
| All three YAML compositions | `config.py`, `test_scripted_ai.py` | Count and list formats supported; current working file uses 1 human + 2 AI |
| Waiting room, two discussions and two votes | `engine.py` | Server-owned state machine; tests passed |
| One valid vote per player per round | `engine.py`, `schema.sql` | At most one accepted vote; missing ballots are abstentions |
| Deadline progression and totals | `engine.py`, `main.py` | Tested; totals combine rounds and ties break alphabetically |
| Scripted AI sends chat and votes | `scripted_ai.py`, `session.py` | Tested; no external LLM API or keys |
| Hidden roles | Public-state builder and broadcast envelopes | No role fields sent; behavioral inference remains possible |
| Private identity and refresh/reconnect | Token hub and `useExperiment.js` | Protocol tests passed; full browser refresh test pending |
| PostgreSQL records and safe queries | `storage.py`, `schema.sql` | Prior real PostgreSQL run passed; current review did not rerun database tests |
| Static React served by FastAPI | Dockerfile, static mount, `/api/join` alias | Routing test and frontend build passed |
| One-command Compose on port 8081 | `compose.yml`, Dockerfile | Files reviewed; actual Docker build/startup not verified |
| Credentials not hardcoded | Generated password volume and ignored local files | No credential candidates found by scoped Git audit |
| README and truthful AI-use record | README.md, ai_prompts.md | Updated; exact model revision remains unverified |

## Findings and remaining issues

1. **Deployment verification is incomplete.** Docker is unavailable here. Run a
   fresh-volume `docker compose up --build` before submission; check the UI and
   `/health`, and inspect database rows. The configured image is PostgreSQL 17,
   whereas the previous real database tests used installed PostgreSQL 18.
   The database healthcheck currently uses a local socket (`pg_isready` without
   `-h`), while the application connects over TCP. Specifically verify cold-start
   readiness ordering; a TCP healthcheck would more directly match the app's
   connectivity. No Compose changes were made during this review.
2. **No visual browser walkthrough has been performed.** Build/protocol/network
   checks do not prove layout, click behavior, keyboard navigation, or refresh
   behavior end-to-end. Check these manually on desktop and a narrow viewport.
3. **Exact development model provenance is missing.** The interface is Codex and
   actual tool names are recorded, but a verifiable model identifier/revision is
   not available. Supply a genuine contemporaneous record if required; do not
   replace this gap with a guessed model name.
4. **Anonymity is limited to system disclosure.** Scripted wording, immediate phase
   responses, and fixed voting patterns may let participants infer who is AI.
   The stronger reading that humans must never know or infer roles is not proven.
5. **Restart recovery is deliberately absent.** Records survive, but active sessions
   and tokens do not. New startup marks unfinished sessions interrupted. This is
   documented and explicitly permitted by the supplied persistence requirements.
6. **Reliability limitations remain.** Synchronous database writes can delay the
   event loop; the previous reconnect test intermittently cancelled during
   TestClient cleanup. Current tests passed, but the flake is not conclusively
   diagnosed. The HTTPX deprecation warning remains non-failing.
7. **Prototype security and reproducibility scope.** No rate limiting, admission
   control, TLS, or explicit WebSocket Origin policy; the Compose app port is
   published on all host interfaces. Use a trusted local environment for review.
   Database credentials are in Docker volumes and must be preserved with data.
   Python transitive dependencies and container tags are not immutable snapshots.
8. **Current configuration differs from HEAD.** The author's pre-existing working
   change sets humans=1, ai=2, discussion_seconds=60 (voting_seconds=30). The README
   reflects that file; ensure the submitted snapshot includes the intended config.

## Git hygiene audit

- Reviewed the 36 tracked files and six reachable commits present at review start.
- No tracked `.env`, private-key/certificate credential files, database data,
  node_modules, dist, Python caches, or virtual environments were found.
- No matches were found for selected private-key, AWS access-key, GitHub token,
  OpenAI-style key, or credential-bearing PostgreSQL URL patterns in tracked file
  contents or reachable history. This heuristic check is not an exhaustive
  credential scanner and does not certify arbitrary text as secret-free.
- `.env`, `.venv`, frontend/node_modules, frontend/dist, and Python caches are
  ignored. `package-lock.json` is intentionally tracked for reproducible npm installs.
- Existing commits predate this review. No commit, push, history rewriting, or
  staging action was performed. Untracked/ignored local build outputs must not be
  included when manually creating a submission ZIP.

## Final author checklist

- [x] Review source against the supplied requirements.
- [x] Finalize README, configuration examples, architecture and known limitations.
- [x] Record the seven available user prompts and actual tool provenance.
- [x] Run current backend suite: 23 passed, 2 database tests skipped.
- [x] Run frontend protocol tests: 4 passed; production build passed.
- [x] Audit tracked files and reachable history using the scoped checks above.
- [ ] Verify the exact development model from an authentic record, or retain the
  explicit unavailable-provenance statement if no such record exists.
- [ ] Run `docker compose config` and `docker compose up --build` on Docker Desktop;
  check both services become healthy and http://localhost:8081 loads.
- [ ] Complete a solo session and then test all-human waiting and multi-client chat
  with separate browser profiles; confirm both votes and final results.
- [ ] Refresh during discussion and after voting; verify the same label, restored
  history, and locked submitted ballot. Check narrow-screen and keyboard usability.
- [ ] Inspect PostgreSQL message/vote/result rows, restart only the app, and verify
  retained records plus a new session/expired-token flow.
- [ ] Review and include the intended config.yml change and final documentation in
  the submission snapshot; exclude ignored build artifacts and credentials.
- [ ] Check any institute-provided submission format, repository access, deadline,
  and AI-disclosure rules not included in this conversation.

No submission or external communication has been made. Author sign-off remains
pending; checked items above record assistant verification, not human review.
