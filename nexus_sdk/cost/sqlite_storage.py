"""
SQLite storage backend for cost tracking.
"""

import os
import sqlite3
import time


class SQLiteCostStorage:
    """SQLite storage backend for cost events."""

    def __init__(self, db_path: str):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cost_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                model TEXT NOT NULL,
                agent TEXT NOT NULL,
                project TEXT DEFAULT '',
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL NOT NULL,
                session_id TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_timestamp
            ON cost_events(timestamp)
        """)
        conn.commit()
        conn.close()

    def record_event(
        self,
        timestamp: float,
        model: str,
        agent: str,
        project: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        session_id: str,
    ) -> None:
        """Record a cost event."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO cost_events
               (timestamp, model, agent, project, tokens_in, tokens_out, cost_usd, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, model, agent, project, tokens_in, tokens_out, cost_usd, session_id),
        )
        conn.commit()
        conn.close()

    def get_monthly_cost(self) -> float:
        """Get current month's total cost."""
        now = time.time()
        t = time.localtime(now)
        month_start = time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1))

        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM cost_events WHERE timestamp >= ?",
            (month_start,),
        ).fetchone()
        conn.close()
        return float(result[0]) if result else 0.0

    def get_daily_breakdown(self, days: int) -> list[dict[str, float | int | str]]:
        """Get daily cost breakdown."""
        cutoff = time.time() - (days * 86400)
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            """SELECT date(timestamp, 'unixepoch', 'localtime') as day,
                      SUM(cost_usd) as total,
                      COUNT(*) as calls
               FROM cost_events
               WHERE timestamp >= ?
               GROUP BY day
               ORDER BY day DESC""",
            (cutoff,),
        ).fetchall()
        conn.close()
        return [{"date": r[0], "cost": r[1], "calls": r[2]} for r in rows]
