# React experiment client

For the full application with PostgreSQL, use `docker compose up --build` from
the repository root and open http://localhost:8081. FastAPI serves the production
build directly; see [deployment instructions](../DEPLOYMENT.md).

Requires Node.js 20.19+ or 22.12+ (tested with Node 24). The app uses React and
Vite with plain CSS; no component library or client-side phase engine.

## Run locally

Terminal 1, from the repository root:

```powershell
# First-time setup, if the virtual environment is not already present:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

Terminal 2, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. In PowerShell, use `npm.cmd` if script execution
policy blocks `npm.ps1`. On macOS/Linux use `.venv/bin/python` for the backend.

Vite forwards `/api/join` to FastAPI's actual `/join` endpoint and proxies `/ws`
with WebSocket support. This follows the
[Vite proxy configuration](https://vite.dev/config/server-options#server-proxy).
No backend or CORS changes were needed. This proxy is a local-development setup;
production hosting will need equivalent HTTP/WebSocket routing.

## Try the experiment

The default configuration requires three human joins. Use separate browser
profiles/browsers for different participants. Tabs in the same browser profile
share localStorage and therefore represent the **same player**; a new connection
replaces the old one. For a solo walkthrough, set `humans: 1` and `ai: 2` in the
root `config.yml`, then restart the backend. Short durations make testing quicker.
The UI never displays roles or composition.

1. Join and wait for the required participants. The server starts automatically.
2. Send a message during discussion and check that other clients receive it.
3. During voting, select a player and submit. The form locks while awaiting
   acknowledgement, then stays locked for that round after `vote_received`.
4. Refresh: the stored token authenticates the same player and restores chat and
   submitted rounds from `welcome`. No extra join is made.
5. Complete round two and see combined totals and the selected Decision Maker.

Network interruptions trigger reconnect attempts. Actions remain disabled until
fresh server state arrives. Close code 4001 stops retries to avoid competing tabs;
the user can choose “Reconnect here”. Code 4401 offers an explicit reset for an
expired identity, which is expected after restarting this in-memory backend.
Tokens are stored only under `group-decision.reconnect-token`, are never shown in
the interface, and are sent in the first WebSocket frame rather than the URL.

The countdown anchors to each server `seconds_remaining` update and interpolates
using `performance.now()`. It never changes phases locally; at zero, actions stop
and the UI waits for the next server state. Network latency may slightly offset
the displayed time. Server validation remains authoritative.

## Structure and verification

- `src/useExperiment.js`: join, localStorage token, socket lifecycle, reconnect,
  pending actions and errors.
- `src/protocol.js`: welcome/state/chat/vote event updates and countdown calculation.
- `src/App.jsx`: the five phase-driven screens; messages render as escaped text.
- `src/styles.css`: responsive layout, readable forms, focus states.

```powershell
npm test
npm run build
```

Four protocol-state tests and the production build passed. A real local network
smoke test also passed through Vite to FastAPI, covering join/waiting, chat, both
voting rounds, final results, and token reconnect. Temporary servers used a short
test configuration without changing `config.yml`, then were stopped.

All 21 backend tests passed on rerun; the first run encountered an intermittent
TestClient cancellation during reconnect cleanup. Backend files were unchanged.
Browser automation was unavailable, so rendered layout and click-through behavior
have not been visually verified.
