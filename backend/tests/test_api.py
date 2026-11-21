import unittest

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import ExperimentConfig
from app.main import create_app
from test_engine import FakeClock


def event(socket, kind):
    for _ in range(100):
        message = socket.receive_json()
        if message["type"] == kind:
            return message
    raise AssertionError(f"No {kind} event received")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.app = create_app(ExperimentConfig(3, 0, 10, 5), clock=self.clock, tick_seconds=0.1)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def join(self):
        response = self.client.post("/join")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["cache-control"], "no-store")
        return response.json()

    def auth(self, socket, identity):
        socket.send_json({"type": "auth", "token": identity["reconnect_token"]})
        welcome = event(socket, "welcome")
        self.assertEqual(welcome["player"], identity["player"])
        return welcome

    def test_join_unique_tokens_waiting_and_capacity(self):
        one, two, three = self.join(), self.join(), self.join()
        self.assertEqual(one["state"]["phase"], "waiting")
        self.assertEqual(two["state"]["phase"], "waiting")
        self.assertEqual(three["state"]["phase"], "discussion")
        self.assertEqual({one["player"], two["player"], three["player"]}, set("ABC"))
        self.assertEqual(len({p["reconnect_token"] for p in (one, two, three)}), 3)
        self.assertEqual(self.client.post("/join").status_code, 409)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_auth_failure_and_malformed_auth(self):
        for payload in ({"type": "auth", "token": "bad"}, {"type": "chat", "text": "hi"}):
            with self.client.websocket_connect("/ws") as socket:
                socket.send_json(payload)
                with self.assertRaises(WebSocketDisconnect) as error:
                    socket.receive_json()
                self.assertEqual(error.exception.code, 4401)

    def test_chat_broadcast_validation_and_reconnect(self):
        one, two = self.join(), self.join()
        with self.client.websocket_connect("/ws") as first, self.client.websocket_connect("/ws") as second:
            self.auth(first, one)
            self.auth(second, two)
            first.send_json({"type": "chat", "text": "early", "round": 1})
            self.assertIn("discussion", event(first, "error")["message"])
            self.join()
            first.send_json({"type": "chat", "text": "hello", "round": 1})
            expected = event(first, "chat")
            self.assertEqual(event(second, "chat"), expected)
            self.assertEqual(expected["player"], one["player"])
            self.assertEqual(set(expected), {"type", "id", "player", "text", "round"})
            for payload in (
                {"type": "chat", "text": " ", "round": 1},
                {"type": "chat", "text": "x" * 1001, "round": 1},
                {"type": "chat", "text": "spoof", "round": 1, "player": two["player"]},
                {"type": "chat", "text": "stale", "round": 2},
                {"type": "vote", "target": "D", "round": 1},
                {"type": "vote", "target": "A", "round": True},
            ):
                first.send_json(payload)
                event(first, "error")
            first.send_text("not JSON")
            event(first, "error")
            first.send_bytes(b"binary")
            event(first, "error")
        with self.client.websocket_connect("/ws") as reconnected:
            welcome = self.auth(reconnected, one)
            self.assertEqual([m["text"] for m in welcome["messages"]], ["hello"])
            self.assertEqual(welcome["voted_rounds"], [])

    def test_votes_broadcast_duplicate_reconnect_and_automatic_finish(self):
        one, two, _ = self.join(), self.join(), self.join()
        with self.client.websocket_connect("/ws") as first, self.client.websocket_connect("/ws") as second:
            self.auth(first, one)
            self.auth(second, two)
            self.clock.now = 110
            first.send_json({"type": "vote", "target": "B", "round": 1})
            received = event(first, "vote_received")
            self.assertEqual(event(second, "vote_received"), received)
            self.assertNotIn("target", received)
            first.send_json({"type": "vote", "target": "C", "round": 1})
            self.assertIn("already voted", event(first, "error")["message"])
        with self.client.websocket_connect("/ws") as socket:
            self.assertEqual(self.auth(socket, one)["voted_rounds"], [1])
            socket.send_json({"type": "vote", "target": "A", "round": 1})
            self.assertIn("already voted", event(socket, "error")["message"])
            self.clock.now = 130
            # No client action: lifespan ticker must deliver final results.
            for _ in range(100):
                state = event(socket, "state")["state"]
                if state["phase"] == "finished":
                    break
            self.assertEqual(state["phase"], "finished")
            self.assertEqual(state["results"], {"totals": {"A": 0, "B": 1, "C": 0}, "winner": "B"})

    def test_reconnect_replaces_existing_connection(self):
        identity = self.join()
        with self.client.websocket_connect("/ws") as old:
            self.auth(old, identity)
            with self.client.websocket_connect("/ws") as new:
                self.auth(new, identity)
                with self.assertRaises(WebSocketDisconnect) as error:
                    while True:
                        old.receive_json()
                self.assertEqual(error.exception.code, 4001)
                self.assertEqual(event(new, "state")["state"]["phase"], "waiting")

    def test_mixed_session_payloads_do_not_reveal_roles(self):
        with TestClient(create_app(ExperimentConfig(2, 1, 10, 5))) as client:
            one = client.post("/join").json()
            two = client.post("/join").json()
            self.assertEqual(set(one), {"player", "reconnect_token", "state"})
            with client.websocket_connect("/ws") as socket:
                self.auth(socket, two)
                state = event(socket, "state")["state"]
                self.assertEqual(set(state), {"players", "phase", "round", "seconds_remaining", "results"})
                self.assertEqual(state["players"], ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
