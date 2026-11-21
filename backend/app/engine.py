"""Synchronous state machine. Call only from one serialized server task/thread."""

from collections import Counter
from collections import deque
from enum import Enum
from random import SystemRandom
from time import monotonic
from typing import Callable

from .config import ExperimentConfig


LABELS = ("A", "B", "C")


class Phase(str, Enum):
    WAITING = "waiting"
    DISCUSSION = "discussion"
    VOTING = "voting"
    FINISHED = "finished"


class ExperimentError(ValueError):
    """An action is invalid for the current session state."""


class ExperimentSession:
    def __init__(self, config: ExperimentConfig, *, clock: Callable[[], float] = monotonic):
        self._config = config
        self._clock = clock
        # Shuffle so a public label never implies a role.
        labels = list(LABELS)
        SystemRandom().shuffle(labels)
        self._human_slots = tuple(labels[:config.humans])
        self._ai_slots = tuple(labels[config.humans:])
        self._joined: set[str] = set()
        self._phase = Phase.WAITING
        self._round = 0
        self._deadline: float | None = None
        self._votes: dict[int, dict[str, str]] = {1: {}, 2: {}}
        self._messages: deque[dict] = deque(maxlen=100)
        self._message_id = 0

    def post_chat(self, player: str, text: str, *, round_number: int) -> dict:
        """Validate discussion chat and retain the last 100 messages for reconnects."""
        self.tick()
        if self._phase != Phase.DISCUSSION:
            raise ExperimentError("Chat is only open during discussion")
        if type(round_number) is not int or round_number != self._round:
            raise ExperimentError("Message belongs to a different round")
        if player not in LABELS:
            raise ExperimentError("Unknown player label")
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            raise ExperimentError("Chat must contain 1 to 1000 characters and not be blank")
        self._message_id += 1
        message = {"id": self._message_id, "player": player, "text": text.strip(), "round": self._round}
        self._messages.append(message)
        return dict(message)

    def chat_history(self) -> list[dict]:
        return [dict(message) for message in self._messages]

    def voted_rounds(self, player: str) -> list[int]:
        """Private reconnect information for the authenticated player only."""
        if player not in LABELS:
            raise ExperimentError("Unknown player label")
        return [number for number, votes in self._votes.items() if player in votes]

    def join_human(self) -> str:
        """Allocate one human slot; the last join starts discussion round one."""
        if self._phase != Phase.WAITING:
            raise ExperimentError("Session has already started")
        label = next(label for label in self._human_slots if label not in self._joined)
        self._joined.add(label)
        if len(self._joined) == len(self._human_slots):
            self._round = 1
            self._phase = Phase.DISCUSSION
            self._deadline = self._clock() + self._config.discussion_seconds
        return label

    def ai_labels(self) -> tuple[str, ...]:
        """SERVER ONLY: assignments for a future AI adapter, never a client payload."""
        return self._ai_slots

    def tick(self) -> None:
        """Advance all expired phases using the server clock, even with no votes."""
        self._advance(self._clock())

    def _advance(self, now: float) -> None:
        while self._deadline is not None and now >= self._deadline:
            # Anchor each next deadline to the previous one, avoiding polling drift.
            if self._phase == Phase.DISCUSSION:
                self._phase = Phase.VOTING
                self._deadline += self._config.voting_seconds
            elif self._round == 1:
                self._round = 2
                self._phase = Phase.DISCUSSION
                self._deadline += self._config.discussion_seconds
            else:
                self._phase = Phase.FINISHED
                self._deadline = None

    def cast_vote(self, voter: str, target: str, *, round_number: int) -> None:
        """Accept one vote per player per round, including self-votes.

        The server adapter must derive voter from its authenticated participant
        binding, not trust a client-supplied identity. round_number rejects stale
        submissions that arrive during a later voting phase.
        """
        self.tick()
        if self._phase != Phase.VOTING:
            raise ExperimentError("Voting is not open")
        if type(round_number) is not int or round_number != self._round:
            raise ExperimentError("Vote belongs to a different round")
        if voter not in LABELS or target not in LABELS:
            raise ExperimentError("Unknown player label")
        votes = self._votes[self._round]
        if voter in votes:
            raise ExperimentError("Player has already voted this round")
        votes[voter] = target
        # Keep the fixed deadline even when everyone votes early.

    def public_state(self) -> dict:
        """Return a fresh, role-free snapshot; results appear only after round two."""
        now = self._clock()
        self._advance(now)
        results = None
        if self._phase == Phase.FINISHED:
            counts = Counter(target for votes in self._votes.values() for target in votes.values())
            totals = {label: counts[label] for label in LABELS}
            results = {
                "totals": totals,
                "winner": min(LABELS, key=lambda label: (-totals[label], label)),
            }
        return {
            "players": list(LABELS),
            "phase": self._phase.value,
            "round": self._round,
            "seconds_remaining": None if self._deadline is None else max(0.0, self._deadline - now),
            "results": results,
        }
