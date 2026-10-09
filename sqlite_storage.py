"""SQLite-backed trip-session persistence."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .domain import TripSession


class SQLiteTripSessionStore:
    """Persist TripSession JSON in a small local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_sessions (
                    trip_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create(self, session: TripSession) -> TripSession:
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO trip_sessions (trip_id, payload) VALUES (?, ?)",
                    (session.trip_id, session.model_dump_json()),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"trip session already exists: {session.trip_id}") from error
        return session

    def get(self, trip_id: str) -> TripSession | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload FROM trip_sessions WHERE trip_id = ?",
                (trip_id,),
            ).fetchone()
        return TripSession.model_validate_json(row[0]) if row else None

    def save(self, session: TripSession) -> TripSession:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO trip_sessions (trip_id, payload) VALUES (?, ?)
                ON CONFLICT(trip_id) DO UPDATE SET payload = excluded.payload
                """,
                (session.trip_id, session.model_dump_json()),
            )
        return session
