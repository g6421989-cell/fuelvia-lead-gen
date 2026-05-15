# ============================================================
# QUOTA MANAGER - Daily Search Limits
# ============================================================
# 3 searches per day, 30 leads per search = 90 leads/day
# Resets at midnight (based on system date)
# Stored in quota_data.json (no extra database needed)
# ============================================================

import json
import os
from datetime import datetime, date

QUOTA_FILE = os.path.join(os.path.dirname(__file__), "quota_data.json")

MAX_SEARCHES    = 3
LEADS_PER_SEARCH = 30
MAX_LEADS       = MAX_SEARCHES * LEADS_PER_SEARCH  # 90


def _load() -> dict:
    """Load quota data, resetting if it's a new day."""
    today = date.today().isoformat()
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE) as f:
                data = json.load(f)
            if data.get("date") == today:
                return data
        except Exception:
            pass
    # New day — reset
    data = {"date": today, "searches_used": 0, "leads_collected": 0}
    _save(data)
    return data


def _save(data: dict):
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_quota() -> dict:
    """Return full quota state for the UI."""
    data = _load()
    searches_left = MAX_SEARCHES - data["searches_used"]

    # Minutes until midnight
    now = datetime.now()
    midnight = datetime.combine(date.today(), datetime.max.time()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    midnight = midnight + timedelta(days=1)
    diff = midnight - now
    hours_left   = int(diff.seconds // 3600)
    minutes_left = int((diff.seconds % 3600) // 60)

    return {
        "searches_used":   data["searches_used"],
        "searches_max":    MAX_SEARCHES,
        "searches_left":   searches_left,
        "leads_collected": data["leads_collected"],
        "leads_max":       MAX_LEADS,
        "leads_per_search": LEADS_PER_SEARCH,
        "can_search":      data["searches_used"] < MAX_SEARCHES,
        "date":            data["date"],
        "reset_in":        f"{hours_left}h {minutes_left}m",
    }


def use_search() -> bool:
    """
    Consume one search slot.
    Returns True if successful, False if daily limit already reached.
    """
    data = _load()
    if data["searches_used"] >= MAX_SEARCHES:
        return False
    data["searches_used"] += 1
    _save(data)
    return True


def add_leads(count: int):
    """Record that `count` leads were collected in this search."""
    data = _load()
    data["leads_collected"] = min(data["leads_collected"] + count, MAX_LEADS)
    _save(data)


def rollback_search():
    """
    Undo a search slot if the scrape failed with zero results.
    Prevents wasting quota on broken runs.
    """
    data = _load()
    if data["searches_used"] > 0:
        data["searches_used"] -= 1
        _save(data)
