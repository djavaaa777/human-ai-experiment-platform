"""Server-only experiment configuration."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, repr=False)
class ExperimentConfig:
    humans: int
    ai: int
    discussion_seconds: int
    voting_seconds: int

    def __post_init__(self):
        values = (self.humans, self.ai, self.discussion_seconds, self.voting_seconds)
        if any(type(value) is not int for value in values):
            raise ValueError("Configuration values must be integers")
        if not (1 <= self.humans <= 3 and 0 <= self.ai <= 2 and self.humans + self.ai == 3):
            raise ValueError("Exactly three players are required, including at least one human")
        if self.discussion_seconds <= 0 or self.voting_seconds <= 0:
            raise ValueError("Phase durations must be positive")


def load_config(path: str | Path) -> ExperimentConfig:
    """Read YAML without exposing its contents through the public session API."""
    with Path(path).open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or set(data) != {"participants", "discussion_seconds", "voting_seconds"}:
        raise ValueError("Expected participants, discussion_seconds, and voting_seconds")
    participants = data["participants"]
    if not isinstance(participants, dict) or set(participants) != {"humans", "ai"}:
        raise ValueError("Expected participants.humans and participants.ai")
    return ExperimentConfig(**participants, discussion_seconds=data["discussion_seconds"],
                            voting_seconds=data["voting_seconds"])
