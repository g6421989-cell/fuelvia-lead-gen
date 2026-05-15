# ============================================================
# CHANNEL BLACKLIST — Permanent SQLite store
# ============================================================
# Once a channel ID is added it is NEVER removed.
# Purpose: prevent re-scraping the same channel across runs,
#          avoiding duplicate Notion entries & wasted API quota.
# ============================================================

import sqlite3
import os
from datetime import datetime

# DB lives next to this file — survives server restarts forever
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channel_blacklist.db")


def _conn():
    """Open connection and ensure table exists."""
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.execute("""
        CREATE TABLE IF NOT EXISTS scraped_channels (
            channel_id   TEXT PRIMARY KEY,
            channel_name TEXT DEFAULT '',
            added_at     TEXT DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    return con


def is_blacklisted(channel_id: str) -> bool:
    """Return True if this channel has ever been scraped before."""
    if not channel_id:
        return False
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM scraped_channels WHERE channel_id = ?",
            (channel_id,)
        ).fetchone()
    return row is not None


def add_to_blacklist(channel_id: str, channel_name: str = "") -> None:
    """
    Permanently record this channel ID.
    Uses INSERT OR IGNORE — safe to call multiple times.
    """
    if not channel_id:
        return
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO scraped_channels (channel_id, channel_name) VALUES (?, ?)",
            (channel_id, channel_name or "")
        )
        con.commit()


def blacklist_size() -> int:
    """Return total number of blacklisted channel IDs."""
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM scraped_channels").fetchone()[0]


def is_db_ready() -> bool:
    """Quick health-check used at startup."""
    try:
        blacklist_size()
        return True
    except Exception:
        return False
