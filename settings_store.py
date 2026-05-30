# ============================================================
# SETTINGS STORE — Runtime-editable config (UI-managed)
# ============================================================
# Single source of truth for API keys & tunables that can be
# changed from the dashboard WITHOUT a code change or restart.
#
# Resolution order for every key:
#   1. runtime_settings.json  (set from the UI)   ← highest priority
#   2. environment variable    (.env / Render)
#   3. schema default
#
# Consumers MUST read live via get()/get_list() at CALL TIME
# (not import time) so UI edits take effect immediately.
# ============================================================

import os
import json
import threading
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # ensure .env is loaded regardless of import order
except Exception:
    pass

_SETTINGS_FILE = Path(__file__).parent / "runtime_settings.json"
_lock = threading.RLock()
_cache = None  # in-memory cache of the JSON file

# ── Schema: defines every UI-editable setting ───────────────────────
# group  → UI section heading
# label  → human label
# secret → masked in GET responses (only last 4 chars shown)
# kind   → "str" | "int" | "list" (list = newline/comma separated)
# env    → environment variable name(s) to fall back to (first match wins)
# default→ used if neither JSON nor env provides a value
SCHEMA = {
    # ── Claude / LLM ──
    "CLAUDE_API_KEY": {
        "group": "Claude AI", "label": "Claude API Key", "secret": True, "kind": "str",
        "env": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"], "default": "",
    },
    "CLAUDE_BASE_URL": {
        "group": "Claude AI", "label": "Claude Base URL (chat completions endpoint)", "secret": False, "kind": "str",
        "env": ["CLAUDE_BASE_URL"], "default": "https://api.aicredits.in/v1/chat/completions",
    },
    "CLAUDE_MODEL": {
        "group": "Claude AI", "label": "Claude Model", "secret": False, "kind": "str",
        "env": ["CLAUDE_MODEL"], "default": "anthropic/claude-sonnet-4-20250514",
    },

    # ── Notion ──
    "NOTION_API_KEY": {
        "group": "Notion", "label": "Notion API Key", "secret": True, "kind": "str",
        "env": ["NOTION_API_KEY"], "default": "",
    },
    "NOTION_DATABASE_ID": {
        "group": "Notion", "label": "Notion Database ID", "secret": False, "kind": "str",
        "env": ["NOTION_DATABASE_ID"], "default": "",
    },

    # ── YouTube ──
    "YOUTUBE_API_KEYS": {
        "group": "YouTube", "label": "YouTube API Keys (one per line)", "secret": True, "kind": "list",
        "env": [], "default": [],
    },

    # ── Sending mode (Direct SMTP vs Instantly.ai) ──
    "SEND_MODE": {
        "group": "Sending Mode", "label": "Email Sending Method", "secret": False,
        "kind": "choice", "choices": ["smtp", "instantly"],
        "env": ["SEND_MODE"], "default": "smtp",
    },
    "INSTANTLY_API_KEY": {
        "group": "Sending Mode", "label": "Instantly API Key", "secret": True, "kind": "str",
        "env": ["INSTANTLY_API_KEY"], "default": "",
    },
    "INSTANTLY_CAMPAIGN_ID": {
        "group": "Sending Mode", "label": "Instantly Campaign ID", "secret": False, "kind": "str",
        "env": ["INSTANTLY_CAMPAIGN_ID"], "default": "",
    },

    # ── System tunables ──
    "EMAIL_ROTATION_DELAY": {
        "group": "System", "label": "Delay Between Emails (seconds)", "secret": False, "kind": "int",
        "env": ["EMAIL_ROTATION_DELAY"], "default": 600,
    },
    "MAX_EMAILS_PER_ACCOUNT_PER_DAY": {
        "group": "System", "label": "Max Emails / Account / Day", "secret": False, "kind": "int",
        "env": ["MAX_EMAILS_PER_ACCOUNT_PER_DAY"], "default": 40,
    },
}


# ── Internal: load / save JSON ──────────────────────────────────────
def _load():
    global _cache
    with _lock:
        if _cache is None:
            if _SETTINGS_FILE.exists():
                try:
                    _cache = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    _cache = {}
            else:
                _cache = {}
        return _cache


def _save(data):
    global _cache
    with _lock:
        _cache = data
        _SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _coerce(key, value):
    """Coerce a raw value to the schema kind."""
    spec = SCHEMA.get(key, {})
    kind = spec.get("kind", "str")
    if kind == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return spec.get("default", 0)
    if kind == "choice":
        v = str(value).strip().lower()
        choices = spec.get("choices", [])
        return v if v in choices else spec.get("default", (choices[0] if choices else ""))
    if kind == "list":
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            parts = [p.strip() for p in value.replace(",", "\n").splitlines()]
            return [p for p in parts if p]
        return []
    return "" if value is None else str(value)


# ── Public API ──────────────────────────────────────────────────────
def get(key, default=None):
    """Get a single setting. Order: JSON override → env var → schema default."""
    spec = SCHEMA.get(key, {})
    data = _load()

    # 1. JSON override
    if key in data and data[key] not in (None, "", []):
        return _coerce(key, data[key])

    # 2. Environment variable(s)
    for env_name in spec.get("env", []):
        env_val = os.getenv(env_name)
        if env_val:
            return _coerce(key, env_val)

    # 3. Default
    if default is not None:
        return default
    return spec.get("default", "")


def get_list(key):
    """Get a list setting (e.g. YouTube keys). Falls back to numbered env vars."""
    spec = SCHEMA.get(key, {})
    data = _load()

    # 1. JSON override
    if key in data and data[key]:
        return _coerce(key, data[key])

    # 2. Special: YouTube numbered env vars (YOUTUBE_API_1..8 / _KEY_1..8)
    if key == "YOUTUBE_API_KEYS":
        keys = []
        for i in range(1, 13):
            v = os.getenv(f"YOUTUBE_API_KEY_{i}") or os.getenv(f"YOUTUBE_API_{i}")
            if v:
                keys.append(v.strip())
        if keys:
            return keys

    return _coerce(key, spec.get("default", []))


def set_many(updates: dict):
    """
    Persist a batch of settings. Empty/blank values are IGNORED for
    secret fields (so you don't wipe a key by submitting the masked form),
    but explicit clears can be done with the literal '__CLEAR__' token.
    Returns the list of keys actually changed.
    """
    data = dict(_load())
    changed = []
    for key, raw in updates.items():
        if key not in SCHEMA:
            continue
        spec = SCHEMA[key]

        # Explicit clear
        if raw == "__CLEAR__":
            if key in data:
                del data[key]
                changed.append(key)
            continue

        coerced = _coerce(key, raw)

        # Don't overwrite a secret with a blank submission (masked form)
        if spec.get("secret") and (coerced == "" or coerced == []):
            continue
        # Don't store empty non-secret strings either (let env/default win)
        if coerced in ("", []) and spec.get("kind") != "int":
            if key in data:
                del data[key]
                changed.append(key)
            continue

        data[key] = coerced
        changed.append(key)

    _save(data)
    return changed


def _mask(value):
    s = str(value)
    if len(s) <= 4:
        return "••••"
    return "••••" + s[-4:]


def get_all_for_ui():
    """Return all settings grouped for the UI, with secrets masked."""
    groups = {}
    for key, spec in SCHEMA.items():
        grp = spec["group"]
        groups.setdefault(grp, [])

        if spec["kind"] == "list":
            raw = get_list(key)
            display = "\n".join(raw)
            has_value = bool(raw)
            # Mask each line for secrets
            if spec.get("secret") and raw:
                display = "\n".join(_mask(v) for v in raw)
        else:
            raw = get(key)
            has_value = raw not in (None, "", 0) or spec["kind"] == "int"
            display = _mask(raw) if (spec.get("secret") and raw) else raw

        # Source: where the active value comes from
        data = _load()
        if key in data and data[key] not in (None, "", []):
            source = "saved"
        elif _has_env(spec) or (key == "YOUTUBE_API_KEYS" and get_list(key)):
            source = "env"
        else:
            source = "default"

        groups[grp].append({
            "key": key,
            "label": spec["label"],
            "secret": spec.get("secret", False),
            "kind": spec["kind"],
            "choices": spec.get("choices", []),
            "value": display,
            "has_value": has_value,
            "source": source,
        })
    return groups


def _has_env(spec):
    for env_name in spec.get("env", []):
        if os.getenv(env_name):
            return True
    return False


def reload():
    """Force re-read of the JSON file (clears in-memory cache)."""
    global _cache
    with _lock:
        _cache = None
