from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import load_config
from app.engine import ExperimentSession
from app.main import create_app
from app.session import SessionHub
from test_engine import FakeClock
from test_api import event


class ScriptedTests(unittest.TestCase):
    def config(self, humans):
        roles = ["human"] * humans + ["ai"] * (3 - humans)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yml"
            path.write_text(f"participants: {roles}\ndiscussion_seconds: 10\nvoting_seconds: 5\n", encoding="utf-8")
            return load_config(path)

    def test_all_yaml_compositions_complete_with_ai_chat_and_votes(self):
        for humans in (3, 2, 1):
            with self.subTest(humans=humans):
                clock = FakeClock()
                hub = SessionHub(ExperimentSession(self.config(humans), clock=clock))
                for _ in range(humans):
                    hub.tick()
                    self.assertEqual(hub.engine.public_state()["phase"], "waiting")
                    self.assertEqual(hub.engine.chat_history(), [])
                    identity = hub.join()
                self.assertEqual(identity["state"]["phase"], "discussion")
                queue = hub.connect(identity["player"])
                ai = hub.engine.ai_labels()
                self.assertEqual(len(ai), 3 - humans)
                for now in (100, 110, 115, 125):
                    clock.now = now
                    hub.tick()
                    hub.tick()  # Repeated scheduling must never duplicate an action.
                clock.now = 130
                hub.tick()
                messages = hub.engine.chat_history()
                self.assertEqual(len(messages), 2 * len(ai))
                for player in ai:
                    self.assertEqual([m["round"] for m in messages if m["player"] == player], [1, 2])
                    self.assertEqual(hub.engine.voted_rounds(player), [1, 2])
                results = hub.engine.public_state()["results"]
                self.assertEqual(sum(results["totals"].values()), 2 * len(ai))
                events = []
                while not queue.empty():
                    events.append(queue.get_nowait())
                chats = [e for e in events if e["type"] == "chat"]
                votes = [e for e in events if e["type"] == "vote_received"]
                self.assertEqual(len(chats), 2 * len(ai))
                self.assertEqual(len(votes), 2 * len(ai))
                for chat in chats:
                    self.assertEqual(set(chat), {"type", "id", "player", "text", "round"})
                for vote in votes:
                    self.assertEqual(set(vote), {"type", "player", "round"})

    def test_shuffle_applied_and_behavior_repeatable_for_same_assignment(self):
        def reorder(labels):
            labels[:] = ["C", "A", "B"]

        histories = []
        for _ in range(2):
            clock = FakeClock()
            with patch("app.engine.SystemRandom") as random:
                random.return_value.shuffle.side_effect = reorder
                engine = ExperimentSession(self.config(1), clock=clock)
                random.return_value.shuffle.assert_called_once()
            hub = SessionHub(engine)
            self.assertEqual(hub.join()["player"], "C")
            self.assertEqual(engine.ai_labels(), ("A", "B"))
            for now in (100, 110, 115, 125, 130):
                clock.now = now
                hub.tick()
            histories.append((engine.chat_history(), engine.public_state()["results"]))
        self.assertEqual(histories[0], histories[1])

    def test_late_tick_does_not_backfill_expired_phases(self):
        clock = FakeClock()
        hub = SessionHub(ExperimentSession(self.config(1), clock=clock))
        hub.join()
        clock.now = 130
        hub.tick()
        self.assertEqual(hub.engine.chat_history(), [])
        self.assertEqual(sum(hub.engine.public_state()["results"]["totals"].values()), 0)

    def test_websocket_receives_ai_events_from_background_scheduler(self):
        clock = FakeClock()
        with TestClient(create_app(self.config(1), clock=clock, tick_seconds=0.1)) as client:
            identity = client.post("/join").json()
            self.assertEqual(set(identity), {"player", "reconnect_token", "state"})
            with client.websocket_connect("/ws") as socket:
                socket.send_json({"type": "auth", "token": identity["reconnect_token"]})
                welcome = event(socket, "welcome")
                # A scheduled message may already be in reconnect history.
                messages = list(welcome["messages"])
                while len(messages) < 2:
                    messages.append(event(socket, "chat"))
                self.assertEqual({m["player"] for m in messages}, set("ABC") - {identity["player"]})
                clock.now = 110
                votes = [event(socket, "vote_received") for _ in range(2)]
                self.assertEqual({v["player"] for v in votes}, set("ABC") - {identity["player"]})
                for vote in votes:
                    self.assertEqual(set(vote), {"type", "player", "round"})
                self.assertEqual(set(event(socket, "state")["state"]),
                                 {"players", "phase", "round", "seconds_remaining", "results"})


if __name__ == "__main__":
    unittest.main()
