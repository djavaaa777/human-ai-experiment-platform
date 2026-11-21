"""Small synchronous PostgreSQL repository for the single-session assessment."""

import os
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb


class PersistenceError(RuntimeError):
    pass


class PostgresStore:
    def __init__(self, connection):
        self.connection = connection
        self.session_id = uuid4()
        self._last_state = None

    @classmethod
    def from_environment(cls):
        if not os.getenv("DATABASE_URL") and not os.getenv("PGHOST"):
            return None  # Preserve the explicit in-memory development/test mode.
        password_file = os.getenv("DB_PASSWORD_FILE")
        kwargs = {"connect_timeout": 5, "options": "-c statement_timeout=5000"}
        if password_file:
            kwargs["password"] = Path(password_file).read_text().strip()
        return cls(psycopg.connect(os.getenv("DATABASE_URL", ""), autocommit=True, **kwargs))

    def start(self, config, ai_labels):
        with self.connection.transaction():
            self.connection.execute(Path(__file__).with_name("schema.sql").read_text())
            # There is exactly one application worker/deployment using this database.
            self.connection.execute("UPDATE sessions SET status = 'interrupted' WHERE status = 'active'")
            self.connection.execute(
                "INSERT INTO sessions (id, config, ai_labels) VALUES (%s, %s, %s)",
                (self.session_id, Jsonb(asdict(config)), Jsonb(list(ai_labels))),
            )

    def save(self, state, *, message=None, vote=None):
        signature = (state["phase"], state["round"], state["results"])
        if signature == self._last_state and message is None and vote is None:
            return
        try:
            with self.connection.transaction():
                if message is not None:
                    self.connection.execute(
                        "INSERT INTO messages (session_id, id, player, round, text) VALUES (%s,%s,%s,%s,%s)",
                        (self.session_id, message["id"], message["player"], message["round"], message["text"]),
                    )
                if vote is not None:
                    self.connection.execute(
                        "INSERT INTO votes (session_id, player, round, target) VALUES (%s,%s,%s,%s)",
                        (self.session_id, vote["player"], vote["round"], vote["target"]),
                    )
                self.connection.execute(
                    "UPDATE sessions SET phase=%s, round=%s, results=%s, status=%s, updated_at=now() WHERE id=%s",
                    (state["phase"], state["round"], Jsonb(state["results"]),
                     "completed" if state["phase"] == "finished" else "active", self.session_id),
                )
            self._last_state = signature
        except psycopg.Error as exc:
            raise PersistenceError("Database write failed; restart the application before continuing") from exc

    def healthy(self):
        try:
            self.connection.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    def close(self):
        self.connection.close()
