from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from watchx.models import Frame

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    command_display TEXT NOT NULL,
    started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invocations (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    sequence INTEGER NOT NULL,
    exit_code INTEGER NOT NULL,
    duration_ms REAL NOT NULL,
    started_at TEXT NOT NULL,
    timed_out INTEGER NOT NULL,
    stdout TEXT NOT NULL,
    stderr TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invocations_run ON invocations(run_id, sequence);
"""


@contextmanager
def open_store(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    try:
        yield conn
    finally:
        conn.close()


class RunStore:
    def __init__(self, path: Path, command_display: str) -> None:
        self._connection_context = open_store(path)
        self._connection = self._connection_context.__enter__()
        cursor = self._connection.execute(
            "INSERT INTO runs(command_display, started_at) VALUES (?, ?)",
            (command_display, datetime.now().isoformat()),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return the new run ID")
        self.run_id = int(cursor.lastrowid)

    def record(self, frame: Frame) -> None:
        result = frame.result
        self._connection.execute(
            """INSERT INTO invocations
               (run_id, sequence, exit_code, duration_ms, started_at, timed_out, stdout, stderr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.run_id,
                frame.sequence,
                result.exit_code,
                result.duration_ms,
                result.started_at.isoformat(),
                int(result.timed_out),
                result.stdout,
                result.stderr,
            ),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection_context.__exit__(None, None, None)


def export_csv(path: Path, run_id: int, output: Path) -> None:
    with open_store(path) as conn:
        rows = conn.execute(
            "SELECT sequence, exit_code, duration_ms, started_at "
            "FROM invocations WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sequence", "exit_code", "duration_ms", "started_at"])
            writer.writerows(rows)
