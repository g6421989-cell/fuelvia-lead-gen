# ============================================================
# DAILY SEND LIMIT — SQLite tracker for 40 emails/account/day
# ============================================================
# Prevents blowing past Gmail safe limits. Tracks per account,
# resets at midnight UTC.
# ============================================================

import sqlite3
import os
from datetime import date

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_send_limit.db")


def _conn():
    """Open connection and ensure table exists."""
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_sends (
            account_email TEXT,
            send_date     TEXT,
            count         INTEGER,
            PRIMARY KEY (account_email, send_date)
        )
    """)
    con.commit()
    return con


def get_today_count(account_email: str) -> int:
    """Get how many emails sent from this account today."""
    today = date.today().isoformat()
    with _conn() as con:
        row = con.execute(
            "SELECT count FROM daily_sends WHERE account_email = ? AND send_date = ?",
            (account_email.lower(), today)
        ).fetchone()
    return row[0] if row else 0


def increment_today_count(account_email: str) -> int:
    """Increment the count for today and return new count."""
    today = date.today().isoformat()
    account_email = account_email.lower()
    with _conn() as con:
        con.execute("""
            INSERT INTO daily_sends (account_email, send_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(account_email, send_date) DO UPDATE
            SET count = count + 1
        """, (account_email, today))
        con.commit()
        row = con.execute(
            "SELECT count FROM daily_sends WHERE account_email = ? AND send_date = ?",
            (account_email, today)
        ).fetchone()
    return row[0] if row else 1


def has_room_today(account_email: str, limit: int = 40) -> bool:
    """Check if this account has room for one more email today."""
    return get_today_count(account_email) < limit


def reset_expired():
    """Delete records older than today (cleanup)."""
    today = date.today().isoformat()
    with _conn() as con:
        con.execute("DELETE FROM daily_sends WHERE send_date < ?", (today,))
        con.commit()
