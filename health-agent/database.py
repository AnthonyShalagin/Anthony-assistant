"""SQLite database layer with UPSERT semantics."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Optional

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS health_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value REAL,
    unit TEXT,
    recorded_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, source, metric_name)
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    workout_name TEXT NOT NULL,
    exercise TEXT NOT NULL,
    set_order INTEGER NOT NULL,
    weight REAL,
    reps INTEGER,
    volume REAL,
    estimated_1rm REAL,
    recorded_at TEXT DEFAULT (datetime('now')),
    UNIQUE(date, workout_name, exercise, set_order)
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TEXT,
    extra TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_db(db_path: str = DB_PATH):
    """Yield a database connection with WAL mode and foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Create tables if they don't exist."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_metric(
    conn: sqlite3.Connection,
    dt: str,
    source: str,
    metric_name: str,
    value: Optional[float],
    unit: str = "",
) -> None:
    """Insert or update a single health metric."""
    conn.execute(
        """
        INSERT INTO health_metrics (date, source, metric_name, value, unit)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date, source, metric_name)
        DO UPDATE SET value=excluded.value, unit=excluded.unit,
                      recorded_at=datetime('now')
        """,
        (dt, source, metric_name, value, unit),
    )


def upsert_workout(
    conn: sqlite3.Connection,
    dt: str,
    workout_name: str,
    exercise: str,
    set_order: int,
    weight: float,
    reps: int,
    volume: float,
    estimated_1rm: float,
) -> None:
    """Insert or update a workout set."""
    conn.execute(
        """
        INSERT INTO workouts (date, workout_name, exercise, set_order,
                              weight, reps, volume, estimated_1rm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, workout_name, exercise, set_order)
        DO UPDATE SET weight=excluded.weight, reps=excluded.reps,
                      volume=excluded.volume, estimated_1rm=excluded.estimated_1rm,
                      recorded_at=datetime('now')
        """,
        (dt, workout_name, exercise, set_order, weight, reps, volume, estimated_1rm),
    )


def save_oauth_token(
    conn: sqlite3.Connection,
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    token_type: str = "Bearer",
    expires_at: Optional[str] = None,
    extra: Optional[str] = None,
) -> None:
    """Store or refresh an OAuth token."""
    conn.execute(
        """
        INSERT INTO oauth_tokens (provider, access_token, refresh_token,
                                  token_type, expires_at, extra)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider)
        DO UPDATE SET access_token=excluded.access_token,
                      refresh_token=COALESCE(excluded.refresh_token, oauth_tokens.refresh_token),
                      token_type=excluded.token_type,
                      expires_at=excluded.expires_at,
                      extra=excluded.extra,
                      updated_at=datetime('now')
        """,
        (provider, access_token, refresh_token, token_type, expires_at, extra),
    )


def load_oauth_token(conn: sqlite3.Connection, provider: str) -> Optional[dict]:
    """Load an OAuth token for a provider."""
    row = conn.execute(
        "SELECT * FROM oauth_tokens WHERE provider = ?", (provider,)
    ).fetchone()
    return dict(row) if row else None


def get_metrics(
    conn: sqlite3.Connection,
    source: Optional[str] = None,
    days: int = 7,
    metric_name: Optional[str] = None,
) -> list[dict]:
    """Fetch recent health metrics."""
    since = (date.today() - timedelta(days=days)).isoformat()
    query = "SELECT * FROM health_metrics WHERE date >= ?"
    params: list = [since]
    if source:
        query += " AND source = ?"
        params.append(source)
    if metric_name:
        query += " AND metric_name = ?"
        params.append(metric_name)
    query += " ORDER BY date DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_metric_average(
    conn: sqlite3.Connection,
    source: str,
    metric_name: str,
    days: int = 7,
) -> Optional[float]:
    """Calculate the average of a metric over N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    row = conn.execute(
        """
        SELECT AVG(value) as avg_val FROM health_metrics
        WHERE source = ? AND metric_name = ? AND date >= ? AND value IS NOT NULL
        """,
        (source, metric_name, since),
    ).fetchone()
    return row["avg_val"] if row and row["avg_val"] is not None else None


def get_recent_workouts(conn: sqlite3.Connection, days: int = 7) -> list[dict]:
    """Fetch recent workout data."""
    since = (date.today() - timedelta(days=days)).isoformat()
    return [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM workouts WHERE date >= ? ORDER BY date DESC, set_order",
            (since,),
        ).fetchall()
    ]
