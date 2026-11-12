"""SQLite persistence. One connection guarded by a lock: simple and safe for a single-process server."""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, time

from .models import ChildProfile, NotificationEvent, ReminderStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS guardians (
    guardian_id  TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS children (
    child_id       TEXT PRIMARY KEY,
    guardian_id    TEXT NOT NULL REFERENCES guardians(guardian_id),
    display_name   TEXT NOT NULL,
    reminder_time  TEXT NOT NULL,
    window_minutes INTEGER NOT NULL,
    timezone       TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY,
    role       TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    child_id           TEXT NOT NULL REFERENCES children(child_id),
    date_key           TEXT NOT NULL,
    status             TEXT NOT NULL,
    child_marked_at    TEXT,
    adult_confirmed_at TEXT,
    PRIMARY KEY (child_id, date_key)
);
CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guardian_id TEXT NOT NULL,
    child_id    TEXT NOT NULL,
    date_key    TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id    TEXT NOT NULL,
    date_key    TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status   TEXT NOT NULL,
    actor_role  TEXT NOT NULL,
    actor_id    TEXT NOT NULL,
    at          TEXT NOT NULL
);
"""


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Store:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        with self.transaction() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Serialize access and commit (or roll back) as one unit."""
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except BaseException:
                self._conn.rollback()
                raise

    def close(self) -> None:
        self._conn.close()

    # --- guardians / children -------------------------------------------------

    @staticmethod
    def insert_guardian(conn: sqlite3.Connection, guardian_id: str, display_name: str, now: datetime) -> None:
        conn.execute(
            "INSERT INTO guardians (guardian_id, display_name, created_at) VALUES (?, ?, ?)",
            (guardian_id, display_name, now.isoformat()),
        )

    @staticmethod
    def insert_child(conn: sqlite3.Connection, child: ChildProfile, now: datetime) -> None:
        conn.execute(
            "INSERT INTO children (child_id, guardian_id, display_name, reminder_time, window_minutes, timezone, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                child.child_id,
                child.guardian_id,
                child.display_name,
                child.reminder_time.isoformat(),
                child.window_minutes,
                child.timezone,
                now.isoformat(),
            ),
        )

    @staticmethod
    def _child_from_row(row: sqlite3.Row) -> ChildProfile:
        return ChildProfile(
            child_id=row["child_id"],
            guardian_id=row["guardian_id"],
            display_name=row["display_name"],
            reminder_time=time.fromisoformat(row["reminder_time"]),
            window_minutes=row["window_minutes"],
            timezone=row["timezone"],
        )

    def get_child(self, conn: sqlite3.Connection, child_id: str) -> ChildProfile | None:
        row = conn.execute("SELECT * FROM children WHERE child_id = ?", (child_id,)).fetchone()
        return self._child_from_row(row) if row else None

    def list_children(self, conn: sqlite3.Connection, guardian_id: str) -> list[ChildProfile]:
        rows = conn.execute(
            "SELECT * FROM children WHERE guardian_id = ? ORDER BY created_at", (guardian_id,)
        ).fetchall()
        return [self._child_from_row(row) for row in rows]

    # --- tokens ---------------------------------------------------------------

    @staticmethod
    def insert_token(conn: sqlite3.Connection, token_hash: str, role: str, subject_id: str, now: datetime) -> None:
        conn.execute(
            "INSERT INTO tokens (token_hash, role, subject_id, created_at) VALUES (?, ?, ?, ?)",
            (token_hash, role, subject_id, now.isoformat()),
        )

    @staticmethod
    def delete_tokens(conn: sqlite3.Connection, role: str, subject_id: str) -> None:
        conn.execute("DELETE FROM tokens WHERE role = ? AND subject_id = ?", (role, subject_id))

    @staticmethod
    def find_token(conn: sqlite3.Connection, token_hash: str) -> tuple[str, str] | None:
        row = conn.execute("SELECT role, subject_id FROM tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        return (row["role"], row["subject_id"]) if row else None

    # --- reminders ------------------------------------------------------------

    @staticmethod
    def get_or_create_reminder(conn: sqlite3.Connection, child_id: str, date_key: str) -> sqlite3.Row:
        conn.execute(
            "INSERT OR IGNORE INTO reminders (child_id, date_key, status) VALUES (?, ?, ?)",
            (child_id, date_key, ReminderStatus.pending.value),
        )
        return conn.execute(
            "SELECT * FROM reminders WHERE child_id = ? AND date_key = ?", (child_id, date_key)
        ).fetchone()

    @staticmethod
    def update_reminder(
        conn: sqlite3.Connection,
        child_id: str,
        date_key: str,
        status: ReminderStatus,
        child_marked_at: datetime | None,
        adult_confirmed_at: datetime | None,
    ) -> None:
        conn.execute(
            "UPDATE reminders SET status = ?, child_marked_at = ?, adult_confirmed_at = ?"
            " WHERE child_id = ? AND date_key = ?",
            (
                status.value,
                child_marked_at.isoformat() if child_marked_at else None,
                adult_confirmed_at.isoformat() if adult_confirmed_at else None,
                child_id,
                date_key,
            ),
        )

    @staticmethod
    def log_transition(
        conn: sqlite3.Connection,
        child_id: str,
        date_key: str,
        from_status: ReminderStatus,
        to_status: ReminderStatus,
        actor_role: str,
        actor_id: str,
        now: datetime,
    ) -> None:
        conn.execute(
            "INSERT INTO status_log (child_id, date_key, from_status, to_status, actor_role, actor_id, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (child_id, date_key, from_status.value, to_status.value, actor_role, actor_id, now.isoformat()),
        )

    # --- notifications --------------------------------------------------------

    @staticmethod
    def insert_notification(conn: sqlite3.Connection, event: NotificationEvent) -> None:
        conn.execute(
            "INSERT INTO notifications (guardian_id, child_id, date_key, title, body, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (event.guardian_id, event.child_id, event.date_key, event.title, event.body, event.created_at.isoformat()),
        )

    @staticmethod
    def list_notifications(conn: sqlite3.Connection, guardian_id: str) -> list[NotificationEvent]:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE guardian_id = ? ORDER BY id", (guardian_id,)
        ).fetchall()
        return [
            NotificationEvent(
                guardian_id=row["guardian_id"],
                child_id=row["child_id"],
                date_key=row["date_key"],
                title=row["title"],
                body=row["body"],
                created_at=_dt(row["created_at"]),
            )
            for row in rows
        ]


def reminder_times(row: sqlite3.Row) -> tuple[datetime | None, datetime | None]:
    return _dt(row["child_marked_at"]), _dt(row["adult_confirmed_at"])
