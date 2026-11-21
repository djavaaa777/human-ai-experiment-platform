import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from fastapi.testclient import TestClient

from app.config import ExperimentConfig
from app.engine import ExperimentSession
from app.main import create_app
from app.session import SessionHub
from app.storage import PersistenceError, PostgresStore
from test_engine import FakeClock


class DeploymentTests(unittest.TestCase):
    def test_static_frontend_and_join_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("<h1>Experiment frontend</h1>", encoding="utf-8")
            app = create_app(ExperimentConfig(3, 0, 10, 5), static_dir=directory, store_factory=lambda: None)
            with TestClient(app) as client:
                self.assertIn("Experiment frontend", client.get("/").text)
                self.assertEqual(client.get("/health").json(), {"status": "ok"})
                self.assertEqual(client.post("/api/join").status_code, 201)
                self.assertEqual(client.post("/join").status_code, 201)
                self.assertEqual(client.get("/config.yml").status_code, 404)
                self.assertEqual(client.get("/app/schema.sql").status_code, 404)

    def test_write_failure_stops_actions_without_acknowledging(self):
        class BrokenStore:
            def save(self, *args, **kwargs):
                raise PersistenceError("test failure")
        engine = ExperimentSession(ExperimentConfig(1, 2, 10, 5))
        hub = SessionHub(engine)
        identity = hub.join()
        queue = hub.connect(identity["player"])
        hub.store = BrokenStore()
        with self.assertRaises(PersistenceError):
            hub.submit_chat(identity["player"], "uncommitted", round_number=1)
        self.assertTrue(hub.failed)
        self.assertEqual(queue.get_nowait(), {"_close": 1011})
        self.assertTrue(queue.empty())
        with self.assertRaises(PersistenceError):
            hub.join()


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to run real PostgreSQL tests")
class PostgresTests(unittest.TestCase):
    def setUp(self):
        self.connection = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.schema = "test_" + uuid4().hex
        self.connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.cleanup)
        self.config = ExperimentConfig(3, 0, 10, 5)

    def cleanup(self):
        # Only this test's unique schema; no existing research records are touched.
        self.connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.connection.close()

    def test_records_results_parameter_binding_and_restart(self):
        clock = FakeClock()
        engine = ExperimentSession(self.config, clock=clock)
        store = PostgresStore(self.connection)
        store.start(self.config, engine.ai_labels())
        hub = SessionHub(engine, store)
        for _ in range(3):
            hub.join()
        malicious = "It's a message'); DROP TABLE votes; --"
        for _ in range(105):
            hub.submit_chat("A", malicious, round_number=1)
        self.assertEqual(len(engine.chat_history()), 100)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM messages").fetchone()[0], 105)
        self.assertEqual(self.connection.execute("SELECT text FROM messages LIMIT 1").fetchone()[0], malicious)
        for now, round_number in ((110, 1), (125, 2)):
            clock.now = now
            for player in "ABC":
                hub.submit_vote(player, "B", round_number=round_number)
        clock.now = 130
        hub.tick()
        row = self.connection.execute("SELECT status, results FROM sessions WHERE id=%s", (store.session_id,)).fetchone()
        self.assertEqual(row, ("completed", {"totals": {"A": 0, "B": 6, "C": 0}, "winner": "B"}))
        self.assertEqual(self.connection.execute("SELECT count(*) FROM votes").fetchone()[0], 6)
        next_store = PostgresStore(self.connection)
        next_store.start(self.config, ())
        self.assertNotEqual(store.session_id, next_store.session_id)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM messages").fetchone()[0], 105)
        third_store = PostgresStore(self.connection)
        third_store.start(self.config, ())
        self.assertEqual(self.connection.execute("SELECT status FROM sessions WHERE id=%s", (next_store.session_id,)).fetchone()[0], "interrupted")
        self.assertEqual(self.connection.execute("SELECT status FROM sessions WHERE id=%s", (store.session_id,)).fetchone()[0], "completed")

    def test_database_rejects_duplicate_vote_and_rolls_back(self):
        store = PostgresStore(self.connection)
        store.start(self.config, ())
        state = {"phase": "voting", "round": 1, "results": None}
        vote = {"player": "A", "target": "B", "round": 1}
        store.save(state, vote=vote)
        with self.assertRaises(PersistenceError):
            store.save(state, vote=vote, message={"id": 1, "player": "A", "round": 1, "text": "must roll back"})
        self.assertEqual(self.connection.execute("SELECT count(*) FROM messages").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM votes").fetchone()[0], 1)
        self.assertTrue(store.healthy())


if __name__ == "__main__":
    unittest.main()
