"""In-memory identity and delivery adapter. All methods run on one event loop."""

import asyncio
import secrets

from .engine import ExperimentSession
from .scripted_ai import ScriptedPlayers


class SessionHub:
    def __init__(self, engine: ExperimentSession):
        self.engine = engine
        self._tokens: dict[str, str] = {}
        self._connections: dict[str, asyncio.Queue] = {}
        self._scripted_players = ScriptedPlayers(engine.ai_labels())

    def tick(self) -> None:
        self.engine.tick()
        self._scripted_players.step(self)
        self.broadcast_state()

    def join(self) -> dict:
        player = self.engine.join_human()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = player
        self.broadcast_state()
        return {"player": player, "reconnect_token": token, "state": self.engine.public_state()}

    def authenticate(self, token: str) -> str | None:
        return self._tokens.get(token)

    def connect(self, player: str) -> asyncio.Queue:
        old = self._connections.get(player)
        if old is not None:
            self._close_queue(old, 4001)
        queue = asyncio.Queue(maxsize=256)
        self._connections[player] = queue
        self.send(queue, {"type": "welcome", "player": player,
                          "voted_rounds": self.engine.voted_rounds(player),
                          "messages": self.engine.chat_history()})
        self.send(queue, self.state_event())
        return queue

    def is_current(self, player: str, queue: asyncio.Queue) -> bool:
        return self._connections.get(player) is queue

    def disconnect(self, player: str, queue: asyncio.Queue) -> None:
        if self.is_current(player, queue):
            del self._connections[player]

    @staticmethod
    def _close_queue(queue: asyncio.Queue, code: int) -> None:
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait({"_close": code})

    def send(self, queue: asyncio.Queue, event: dict) -> None:
        if queue.full():
            self._close_queue(queue, 1013)
            for player, current in list(self._connections.items()):
                if current is queue:
                    del self._connections[player]
        else:
            queue.put_nowait(event)

    def broadcast(self, event: dict) -> None:
        for queue in list(self._connections.values()):
            self.send(queue, event)

    def state_event(self) -> dict:
        return {"type": "state", "state": self.engine.public_state()}

    def broadcast_state(self) -> None:
        self.broadcast(self.state_event())

    def handle(self, player: str, action) -> None:
        if action.type == "chat":
            self.submit_chat(player, action.text, round_number=action.round)
        else:
            self.submit_vote(player, action.target, round_number=action.round)

    def submit_chat(self, player: str, text: str, *, round_number: int) -> None:
        message = self.engine.post_chat(player, text, round_number=round_number)
        self.broadcast({"type": "chat", **message})
        self.broadcast_state()

    def submit_vote(self, player: str, target: str, *, round_number: int) -> None:
        self.engine.cast_vote(player, target, round_number=round_number)
        # Human and scripted players use identical public envelopes.
        self.broadcast({"type": "vote_received", "player": player, "round": round_number})
        self.broadcast_state()
