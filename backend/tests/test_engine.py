import json
from pathlib import Path
import tempfile
import unittest

from app.config import ExperimentConfig, load_config
from app.engine import ExperimentError, ExperimentSession


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class EngineTests(unittest.TestCase):
    def make_session(self, humans=3):
        self.clock = FakeClock()
        return ExperimentSession(ExperimentConfig(humans, 3 - humans, 10, 5), clock=self.clock)

    def start(self, humans=3):
        session = self.make_session(humans)
        for _ in range(humans):
            session.join_human()
        return session

    def test_waits_for_all_humans_in_every_composition(self):
        for humans in (1, 2, 3):
            with self.subTest(humans=humans):
                session = self.make_session(humans)
                joined = []
                for _ in range(humans):
                    self.clock.now += 100
                    session.tick()
                    self.assertEqual(session.public_state()["phase"], "waiting")
                    self.assertIsNone(session.public_state()["seconds_remaining"])
                    joined.append(session.join_human())
                self.assertEqual(len(set(joined)), humans)
                self.assertEqual(set(joined) | set(session.ai_labels()), {"A", "B", "C"})
                self.assertFalse(set(joined) & set(session.ai_labels()))
                self.assertEqual(session.public_state()["phase"], "discussion")
                with self.assertRaises(ExperimentError):
                    session.join_human()

    def test_two_rounds_advance_at_exact_deadlines_without_votes(self):
        session = self.start()
        for time, phase, round_number, remaining in (
            (109.9, "discussion", 1, 0.1),
            (110, "voting", 1, 5),
            (115, "discussion", 2, 10),
            (125, "voting", 2, 5),
            (130, "finished", 2, None),
        ):
            self.clock.now = time
            session.tick()
            state = session.public_state()
            self.assertEqual((state["phase"], state["round"]), (phase, round_number))
            if remaining is None:
                self.assertIsNone(state["seconds_remaining"])
            else:
                self.assertAlmostEqual(state["seconds_remaining"], remaining)

    def test_delayed_tick_catches_up_and_finished_state_is_stable(self):
        session = self.start()
        self.clock.now = 1000
        session.tick()
        before = session.public_state()
        session.tick()
        self.assertEqual(session.public_state(), before)
        self.assertEqual(before["phase"], "finished")

    def test_duplicate_vote_rejected_but_next_round_allowed(self):
        session = self.start()
        self.clock.now = 110
        session.cast_vote("A", "A", round_number=1)
        with self.assertRaises(ExperimentError):
            session.cast_vote("A", "B", round_number=1)
        self.clock.now = 125
        session.cast_vote("A", "C", round_number=2)
        self.clock.now = 130
        self.assertEqual(session.public_state()["results"]["totals"], {"A": 1, "B": 0, "C": 1})

    def test_invalid_phase_labels_stale_round_and_expired_vote_rejected(self):
        session = self.start()
        with self.assertRaises(ExperimentError):
            session.cast_vote("A", "B", round_number=1)
        self.clock.now = 110
        for voter, target in (("D", "A"), ("A", "D")):
            with self.assertRaises(ExperimentError):
                session.cast_vote(voter, target, round_number=1)
        self.clock.now = 115
        with self.assertRaises(ExperimentError):
            session.cast_vote("A", "B", round_number=1)
        self.clock.now = 125
        with self.assertRaises(ExperimentError):
            session.cast_vote("A", "B", round_number=1)
        self.clock.now = 130
        with self.assertRaises(ExperimentError):
            session.cast_vote("A", "B", round_number=2)

    def test_results_sum_both_rounds_and_all_players_can_vote(self):
        session = self.start(humans=1)
        self.clock.now = 110
        for voter, target in zip("ABC", "BBC"):
            session.cast_vote(voter, target, round_number=1)
        self.assertEqual(session.public_state()["phase"], "voting")
        self.assertIsNone(session.public_state()["results"])
        self.clock.now = 125
        for voter, target in zip("ABC", "ABC"):
            session.cast_vote(voter, target, round_number=2)
        self.clock.now = 130
        self.assertEqual(session.public_state()["results"], {
            "totals": {"A": 1, "B": 3, "C": 2}, "winner": "B",
        })

    def test_ties_and_missing_votes(self):
        session = self.start()
        self.clock.now = 110
        session.cast_vote("A", "C", round_number=1)
        self.clock.now = 125
        session.cast_vote("B", "B", round_number=2)
        self.clock.now = 130
        self.assertEqual(session.public_state()["results"], {
            "totals": {"A": 0, "B": 1, "C": 1}, "winner": "B",
        })
        session = self.start()
        self.clock.now = 130
        self.assertEqual(session.public_state()["results"]["winner"], "A")

    def test_public_snapshot_is_role_free_and_cannot_mutate_session(self):
        snapshots = []
        for humans in (1, 2, 3):
            session = self.make_session(humans)
            state = session.public_state()
            self.assertEqual(set(state), {"players", "phase", "round", "seconds_remaining", "results"})
            snapshots.append(json.dumps(state, sort_keys=True))
            state["players"].clear()
            self.assertEqual(session.public_state()["players"], ["A", "B", "C"])
        self.assertEqual(len(set(snapshots)), 1)


class ConfigTests(unittest.TestCase):
    def test_load_project_yaml(self):
        config = load_config(Path(__file__).resolve().parents[2] / "config.yml")
        self.assertEqual(config.humans + config.ai, 3)

    def test_load_each_composition(self):
        for humans in (1, 2, 3):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "config.yml"
                path.write_text(f"participants:\n  humans: {humans}\n  ai: {3 - humans}\ndiscussion_seconds: 10\nvoting_seconds: 5\n", encoding="utf-8")
                config = load_config(path)
                self.assertEqual((config.humans, config.ai), (humans, 3 - humans))

    def test_invalid_config_rejected(self):
        for values in ((0, 3, 10, 5), (2, 0, 10, 5), (3, 0, 0, 5),
                       (3, 0, 10, -1), (True, 2, 10, 5), (3, 0, 1.5, 5)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ExperimentConfig(*values)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            for data in ("[]", "participants: {}\ndiscussion_seconds: 10\nvoting_seconds: 5"):
                path.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)


if __name__ == "__main__":
    unittest.main()
