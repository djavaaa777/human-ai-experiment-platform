"""Local scripted players: no network, randomness, or model dependencies."""

from .engine import LABELS, ExperimentError


class ScriptedPlayers:
    def __init__(self, labels: tuple[str, ...]):
        self._labels = tuple(sorted(labels))
        self._completed: set[tuple[str, int, str]] = set()

    def step(self, hub) -> None:
        state = hub.engine.public_state()
        phase, round_number = state["phase"], state["round"]
        if phase not in ("discussion", "voting"):
            return
        for player in self._labels:
            key = (player, round_number, phase)
            if key in self._completed:
                continue
            # A nominates B, B nominates C, C nominates A in both rounds.
            target = LABELS[(LABELS.index(player) + 1) % len(LABELS)]
            try:
                if phase == "discussion":
                    text = (f"I suggest {target}. What does everyone think?" if round_number == 1
                            else f"My vote is still for {target}. Let's make our final choice.")
                    hub.submit_chat(player, text, round_number=round_number)
                else:
                    hub.submit_vote(player, target, round_number=round_number)
            except ExperimentError:
                # A deadline may pass between the snapshot and engine validation.
                # Never backfill expired phases or stop the scheduler for that race.
                current = hub.engine.public_state()
                if (current["phase"], current["round"]) != (phase, round_number):
                    return
                raise
            self._completed.add(key)
