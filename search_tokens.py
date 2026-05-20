# ============================================================
# SEARCH TOKEN PERSISTENCE — Fuelvia
# ============================================================
# Saves YouTube nextPageToken per query so every scrape run
# continues from where the last one left off instead of
# restarting from page 1 (which always gives the same results).
#
# File: search_tokens.json
# Key:  "{query}::{location}" → nextPageToken string
# ============================================================

import json
import os
from pathlib import Path

_TOKEN_FILE = Path(__file__).parent / "search_tokens.json"
_USED_KEYWORDS_FILE = Path(__file__).parent / "used_keywords.json"


def _load_tokens() -> dict:
    try:
        if _TOKEN_FILE.exists():
            return json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_tokens(data: dict):
    try:
        _TOKEN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[search_tokens] Could not save tokens: {e}")


def get_token(query: str, location: str = "") -> str | None:
    """Return saved nextPageToken for this query+location, or None if fresh start."""
    key = f"{query}::{location}"
    return _load_tokens().get(key)


def save_token(query: str, location: str, token: str | None):
    """
    Save nextPageToken after a search page.
    Pass token=None to clear (reset to page 1 for next run).
    """
    key = f"{query}::{location}"
    data = _load_tokens()
    if token:
        data[key] = token
    else:
        data.pop(key, None)
    _save_tokens(data)


def clear_all_tokens():
    """Reset all saved tokens — forces page-1 restart on next run."""
    _save_tokens({})
    print("[search_tokens] All page tokens cleared.")


def token_count() -> int:
    return len(_load_tokens())


# ── Used Keywords Tracking ────────────────────────────────────
# Tracks which keyword queries have been used per niche so
# Claude can generate genuinely new variations each run.

def _load_used() -> dict:
    try:
        if _USED_KEYWORDS_FILE.exists():
            return json.loads(_USED_KEYWORDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def get_used_keywords(niche_key: str) -> list:
    """Return list of already-used keyword queries for this niche."""
    return _load_used().get(niche_key, [])


def save_used_keywords(niche_key: str, keywords: list):
    """Add keywords to the used list for this niche (deduped)."""
    data = _load_used()
    existing = set(data.get(niche_key, []))
    existing.update(keywords)
    data[niche_key] = list(existing)
    try:
        _USED_KEYWORDS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[search_tokens] Could not save used keywords: {e}")


def clear_used_keywords(niche_key: str = None):
    """Clear used keywords. Pass niche_key to clear one niche, or None to clear all."""
    if niche_key:
        data = _load_used()
        data.pop(niche_key, None)
        _USED_KEYWORDS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        if _USED_KEYWORDS_FILE.exists():
            _USED_KEYWORDS_FILE.write_text("{}", encoding="utf-8")
