# Server and manual testing

For the complete Docker/PostgreSQL setup use `docker compose up --build` and
http://localhost:8081. See [deployment and persistence](../DEPLOYMENT.md). The
commands below remain useful for separate local development without a database.
`POST /api/join` is now also available as an alias for the built React frontend.

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 16384
```

Create `.venv` first with `python -m venv .venv` if needed. Use a single worker:
identities, chat, ballots, and session state live in process memory. Restarting
resets everything, including tokens. Avoid auto-reload during an experiment.
The server reads the root `config.yml` at startup.

## Endpoints

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Returns `{"status":"ok"}`. |
| `POST /join` | No body. Allocates a human slot and returns HTTP 201 with `player`, `reconnect_token`, and public `state`. Returns 409 after all human slots are allocated. |
| `WS /ws` | Authenticate in the first JSON text frame, then send chat/vote actions and receive events. |
| `GET /docs` | FastAPI's interactive HTTP API documentation. |

`POST /join` creates a new identity every time; never use it to reconnect.
Keep the token private: it is the bearer credential for that player's actions.
Tokens are not included in broadcast messages or URL query strings. Only the
caller receives its join token; the response uses `Cache-Control: no-store`.
The server has no public config or role endpoint and never reports connection
status by player. All public labels are A, B, and C.

## Client WebSocket messages

Send this first, within 10 seconds of opening the connection:

```json
{"type":"auth","token":"TOKEN_FROM_JOIN"}
```

Then, in the appropriate round/phase:

```json
{"type":"chat","text":"I suggest voting for B.","round":1}
{"type":"vote","target":"B","round":1}
```

For round two use `"round":2`. The server derives the sender/voter from the token;
do not send a player identity. Unknown fields and message types, non-integer
rounds, malformed JSON, and binary messages are rejected. Chat must be nonblank
and at most 1000 characters, and is accepted only during the matching discussion.
Votes are accepted only during the matching voting phase, once per player per
round. Self-votes are allowed. The engine enforces these rules.

## Server events

- `welcome`: private reconnect snapshot containing `player`, `voted_rounds`, and
  `messages` (the last 100 accepted chat messages). It does not echo the token.
- `state`: `{"type":"state","state":{"players":["A","B","C"],"phase":"discussion","round":1,"seconds_remaining":119.5,"results":null}}`.
  Sent on connection, after joins/actions, and every 250 ms. The countdown is
  calculated from the server's monotonic deadline. Render/interpolate it locally,
  but accept phase changes only from the server. Network delay can affect display.
- `chat`: `{"type":"chat","id":1,"player":"A","text":"Hello","round":1}`.
  Broadcast to all connected participants, including the sender. Message IDs allow
  clients to deduplicate reconnect history. Treat text as plain text, never HTML.
- `vote_received`: `{"type":"vote_received","player":"A","round":1}`.
  Broadcast to everyone; the ballot target remains private. Reconnect state tells
  the returning player which rounds they have already voted in.
- `error`: `{"type":"error","message":"Player has already voted this round"}`.
  Sent only to the sender, followed by current state; the connection remains open.

Final state has `phase: "finished"`, `seconds_remaining: null`, and results such
as `{"totals":{"A":1,"B":3,"C":2},"winner":"B"}`. Both rounds contribute;
missing votes are abstentions and ties resolve alphabetically, including A winning
an all-zero tie. Voting always ends at its deadline, not when all ballots arrive.

Invalid authentication closes with 4401. Authenticating a new socket with the same
token replaces the old socket (old closes with 4001). Slow clients whose bounded
outbound queue fills are disconnected with 1013 and can reconnect for state/history.
Each socket has one writer so events do not overlap. Socket I/O does not block
the phase scheduler. No durable event replay is provided beyond retained chat,
current state, and the reconnecting participant's voting status.

## Manually test two participants

For a two-person walkthrough, temporarily change `config.yml` to `humans: 2` and
`ai: 1`, and optionally shorten discussion/voting durations to 20/15 seconds.
Restart the server after editing. The third slot will automatically send scripted
discussion messages and vote in both rounds. Restore your desired settings
after the walkthrough. With a three-human configuration, a third join is
required before discussion starts.

1. Open `http://127.0.0.1:8000/docs` in two separate browser tabs. Open each tab's
   developer console. Run this in each tab once:

   ```javascript
   var identity = await fetch('/join', {method: 'POST'}).then(r => r.json());
   sessionStorage.setItem('experimentToken', identity.reconnect_token);
   console.log('My label:', identity.player);
   ```

2. In each console, create the connection helper and connect:

   ```javascript
   var ws;
   var currentState;
   function connectExperiment() {
     ws = new WebSocket('ws://127.0.0.1:8000/ws');
     ws.onopen = () => ws.send(JSON.stringify({
       type: 'auth', token: sessionStorage.getItem('experimentToken')
     }));
     ws.onmessage = e => {
       const message = JSON.parse(e.data);
       if (message.type === 'state') currentState = message.state;
       console.log(message);
     };
     ws.onclose = e => console.log('Closed:', e.code);
   }
   connectExperiment();
   ```

3. During discussion, send from one tab and observe the message in both:

   ```javascript
   ws.send(JSON.stringify({type:'chat', text:'Hello from this player!', round:currentState.round}));
   ```

4. Wait for `phase: "voting"`, then vote in both tabs:

   ```javascript
   ws.send(JSON.stringify({type:'vote', target:'B', round:currentState.round}));
   ```

   Repeat the same command in a tab to see duplicate-vote rejection. Wait for
   round two, discuss and vote again, and check the final totals in both tabs.
   Leave a vote unsubmitted to confirm the deadline still advances automatically.

5. Close a connection using `ws.close()`, then call `connectExperiment()` again.
   Do not call `/join`. Observe the same player label, recent chat, and voting
   status. A page reload preserves `sessionStorage`; redefine the connection
   helper after reloading and reconnect with the stored token.

With three-human configuration, an additional `POST /join` from `/docs` or a third
tab fills the remaining slot; that participant can remain disconnected while you
exercise chat and voting in the first two tabs.

## Tests and boundaries

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

21 tests passed using the in-process FastAPI TestClient and the existing engine
tests. Coverage includes two-client broadcasts, auth rejection, invalid chat and
vote payloads, reconnect replacement/history/voting status, capacity, hidden roles,
automatic deadline completion, and scripted AI chat/voting in all three YAML
configurations. No live browser/network walkthrough was run.
The installed Starlette emits a non-failing deprecation warning about HTTPX in its
test client. TestClient usage follows the official
[FastAPI WebSocket testing documentation](https://fastapi.tiangolo.com/advanced/testing-websockets/).

This local assessment server does not implement admission controls, durable
recovery, participant accounts, frontend, external language models, or database integration.
Disconnects do not free slots or pause deadlines. A lost join response/token is
not recoverable; restart the server to begin a fresh session. Use HTTPS/WSS when
hosting beyond a trusted local environment because tokens grant player access.
