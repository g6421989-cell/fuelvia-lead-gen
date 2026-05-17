"""
FUELVIA WEB APP — DASHBOARD
============================
Flask server for the Fuelvia lead generation dashboard.

Routes:
  GET  /                           → Dashboard (requires login)
  POST /api/login                  → Authenticate
  POST /api/logout                 → Clear session
  GET  /api/dashboard-data         → Overview stats
  GET  /api/leads                  → All leads table
  GET  /api/emails                 → Email log
  GET  /api/replies                → Replies log
  GET  /api/niche-options          → Niche dropdown options
  GET  /api/location-options       → Location dropdown options
  GET  /api/subscriber-range-options → Sub range options
  GET  /api/niche-health           → Intelligence tab niche stats
  GET  /api/expansion-suggestions  → Expansion recommendations
  POST /api/start-scrape           → Start background scrape
  POST /api/pause-scrape           → Pause active scrape
  POST /api/resume-scrape          → Resume paused scrape
  POST /api/stop-scrape            → Stop scrape
  GET  /api/scrape-status          → Live scrape state + logs
  POST /api/send-emails            → Cold email all "New" leads (background)
  POST /api/send-followup          → Follow-up "Contacted" leads (background)
  POST /api/check-replies          → Scan inbox for replies (background)
  GET  /api/email-action-status    → Live email action state + logs
  POST /api/stop-email-action      → Stop the running email action
  POST /admin/change               → Remote config update (admin key)

Run:  python app.py
Open: http://127.0.0.1:5000
Pass: fuelvia2025
"""

import threading
import time
import smtplib
import imaplib
import email as _email_lib
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
import html as _html_mod
import re as _re
import json
import os

from googleapiclient.discovery import build as _yt_build

from flask import Flask, render_template, request, jsonify, session, Response

from config import (
    NICHE_OPTIONS, LOCATION_OPTIONS, SUBSCRIBER_RANGES,
    EMAIL_ROTATION_DELAY, SENDER_NAME, COMPANY_NAME,
    YOUTUBE_APIS,
)
from notion_manager import NotionManager
from claude_helpers import write_personalized_initial_email, write_personalized_followup_1
from youtube_enricher import get_videos_for_channel, days_since_last_video
from lead_intelligence import LeadIntelligence
from scraper_engine import scrape_leads
from daily_send_limit import has_room_today, increment_today_count, reset_expired


# ── App setup ──────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "fuelvia-secret-2026"

DASHBOARD_PASSWORD = "fuelvia2025"
ADMIN_KEY          = "FuelVia_Admin_2026_SecureRemote_Key_xyz789abc123def"


# ── Load email config from environment or JSON ────────────────────────────────
def _load_email_config():
    """Load email accounts from environment variable or fallback to email_config.json"""
    email_config_env = os.getenv("EMAIL_CONFIG")
    if email_config_env:
        try:
            config = json.loads(email_config_env)
            return config.get("outreach_emails", [])
        except Exception as e:
            print(f"WARNING: Could not parse EMAIL_CONFIG env var: {e}")

    # Fallback to JSON file for local development
    config_path = os.path.join(os.path.dirname(__file__), "email_config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("outreach_emails", [])
    except Exception as e:
        print(f"WARNING: Could not load email_config.json: {e}")
        return []

OUTREACH_ACCOUNTS = _load_email_config()
if not OUTREACH_ACCOUNTS:
    print("WARNING: No outreach accounts loaded (EMAIL_CONFIG env or email_config.json)")
else:
    print(f"[OK] Loaded {len(OUTREACH_ACCOUNTS)} email accounts")
    for acc in OUTREACH_ACCOUNTS:
        print(f"     • {acc['email']}")


# ── Global scrape state ────────────────────────────────────────

_scrape_state = {
    "status":      "idle",
    "progress":    0,
    "leads_found": 0,
    "total":       0,
    "logs":        [],
    "thread":      None,
}

_stop_event  = threading.Event()
_pause_event = threading.Event()
_state_lock  = threading.Lock()


# ── Global email-action state ──────────────────────────────────

_email_action_state = {
    "status":   "idle",   # idle | running | completed | stopped | error
    "action":   "",       # send_emails | send_followup | check_replies
    "progress": 0,        # 0-100
    "total":    0,
    "logs":     [],
}

_email_action_stop = threading.Event()
_email_action_lock = threading.Lock()


# ── Shared timestamp helper ────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── Scrape log ─────────────────────────────────────────────────

def _log(msg: str):
    with _state_lock:
        _scrape_state["logs"].append(msg)
        if len(_scrape_state["logs"]) > 500:
            _scrape_state["logs"] = _scrape_state["logs"][-500:]


# ── Email action log ───────────────────────────────────────────

def _alog(msg: str):
    """Append a line to the email-action live log (capped at 300 lines)."""
    with _email_action_lock:
        _email_action_state["logs"].append(msg)
        if len(_email_action_state["logs"]) > 300:
            _email_action_state["logs"] = _email_action_state["logs"][-300:]


# ── Email rotation helper ──────────────────────────────────────

_email_rot_idx  = 0
_email_rot_lock = threading.Lock()


def _next_account():
    global _email_rot_idx
    with _email_rot_lock:
        acc = OUTREACH_ACCOUNTS[_email_rot_idx % len(OUTREACH_ACCOUNTS)]
        _email_rot_idx += 1
    return acc


def _peek_next_account():
    """Show which account will be used next (without incrementing counter)."""
    global _email_rot_idx
    with _email_rot_lock:
        acc = OUTREACH_ACCOUNTS[_email_rot_idx % len(OUTREACH_ACCOUNTS)]
    return acc


def _get_founder_name(email: str) -> str:
    """Extract founder name from email address.

    Examples:
    - jashan@fuelviaa.com → Jashan
    - ruwaid@fuelviaa.com → Ruwaid
    - danish@fuelviaa.com → Danish
    """
    if not email or "@" not in email:
        return SENDER_NAME
    founder_name = email.split("@")[0]  # Get part before @
    return founder_name.capitalize()    # Capitalize first letter


def _smtp_send(account: dict, to_email: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    # ── Use founder name from email address ──
    founder_name = _get_founder_name(account["email"])
    msg["From"]    = f"{founder_name} - {COMPANY_NAME} <{account['email']}>"
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(account["smtp_server"], account["smtp_port"]) as srv:
            srv.starttls()
            srv.login(account["email"], account["password"])
            srv.sendmail(account["email"], to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  [SMTP] Error sending to {to_email}: {e}")
        return False


# ── YouTube re-fetch helper ────────────────────────────────────

_YT_CHANNEL_RE = _re.compile(r'/channel/([A-Za-z0-9_-]{20,})')


def _fetch_youtube_for_lead(youtube_url: str) -> tuple:
    if not youtube_url:
        return {}, []
    m = _YT_CHANNEL_RE.search(youtube_url)
    if not m:
        return {}, []
    channel_id = m.group(1)

    for key in YOUTUBE_APIS:
        try:
            yt   = _yt_build("youtube", "v3", developerKey=key)
            resp = yt.channels().list(
                part="snippet,statistics,contentDetails",
                id=channel_id,
            ).execute()
            items = resp.get("items", [])
            if not items:
                return {}, []
            item    = items[0]
            snippet = item["snippet"]
            stats   = item.get("statistics", {})
            uploads_pid = (
                item.get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
            )
            channel_data = {
                "channel_name":        snippet.get("title", ""),
                "subscriber_count":    int(stats.get("subscriberCount", 0)),
                "description":         snippet.get("description", ""),
                "channel_id":          channel_id,
                "uploads_playlist_id": uploads_pid,
            }
            videos = []
            try:
                videos = get_videos_for_channel(yt, channel_id,
                    uploads_playlist_id=uploads_pid, max_videos=5)
            except Exception:
                pass
            return channel_data, videos
        except Exception as e:
            if "quotaExceeded" in str(e) or "403" in str(e):
                continue
            print(f"  [YT] Error fetching {youtube_url}: {str(e)[:120]}")
            return {}, []
    return {}, []


# ── Email body / date helpers ──────────────────────────────────

def _parse_email_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().isoformat()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        try:
            import email.utils as _eu
            t = _eu.parsedate(date_str)
            if t:
                return datetime(*t[:6]).isoformat()
        except Exception:
            pass
        return datetime.now().isoformat()


def _extract_email_body(msg) -> str:
    plain_parts, html_parts = [], []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if "attachment" in part.get("Content-Disposition", ""):
                continue
            try:
                raw = part.get_payload(decode=True)
                if not raw:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                (plain_parts if ct == "text/plain" else html_parts if ct == "text/html" else []).append(text)
            except Exception:
                pass
    else:
        try:
            raw = msg.get_payload(decode=True)
            if raw:
                charset = msg.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                (html_parts if msg.get_content_type() == "text/html" else plain_parts).append(text)
        except Exception:
            pass
    plain_text = "\n".join(plain_parts).strip()
    if len(plain_text) < 80 and html_parts:
        html_raw = "\n".join(html_parts)
        html_raw = _re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_raw, flags=_re.DOTALL | _re.IGNORECASE)
        html_raw = _re.sub(r'<(?:br|p|div|tr|li|h[1-6])[^>]*>', '\n', html_raw, flags=_re.IGNORECASE)
        html_raw = _re.sub(r'<[^>]+>', '', html_raw)
        html_text = _re.sub(r'\n{3,}', '\n\n', _html_mod.unescape(html_raw).strip())
        return html_text if len(html_text) > len(plain_text) else plain_text
    return plain_text


# ── Notion data helpers ────────────────────────────────────────

def _extract_full_lead(record: dict) -> dict:
    props = record.get("properties") or {}

    def _field(name: str):
        v = props.get(name)
        if v is None:
            for k in props:
                if k.strip() == name.strip():
                    v = props[k]
                    break
        return v or {}

    def txt(name: str) -> str:
        f = _field(name)
        blocks = f.get("title") or f.get("rich_text") or []
        return "".join((b.get("text") or {}).get("content", "") for b in blocks)

    def select_val(name: str) -> str:
        return ((_field(name).get("select")) or {}).get("name", "") or ""

    def date_val(name: str) -> str:
        return ((_field(name).get("date")) or {}).get("start", "") or ""

    def num_val(name: str) -> int:
        return _field(name).get("number") or 0

    def bool_val(name: str) -> bool:
        # "checkbox" key can exist with null value → bool(None) = False, which is correct
        return bool(_field(name).get("checkbox") or False)

    def url_val(name: str) -> str:
        return _field(name).get("url", "") or ""

    def email_val(name: str) -> str:
        return _field(name).get("email", "") or ""

    return {
        "id":              record.get("id", ""),
        "channel_name":    txt("Channel Name"),
        "email":           email_val("Email"),
        "subscriber_count": num_val("Subscriber Count"),
        "niche":           select_val("Niche"),
        "location":        txt("Location"),
        "score":           num_val("Score"),
        "status":          select_val("Status") or "New",
        "replied":         bool_val("Replied"),
        "email_sent_from": txt("Email Sent From"),
        "date_added":      date_val("Date Added"),
        "last_contact":    date_val("Last Contact"),
        "reply_date":      date_val("Reply Date"),
        "reply_message":   txt("Reply Message"),
        "day1_email_body": txt("Day 1 Email Body"),
        "day2_sent":       bool_val("Day 2 Sent"),
        "notes":           txt("Notes"),
        "youtube_url":     url_val("YouTube URL"),
    }


# ── Auth ───────────────────────────────────────────────────────

def _auth() -> bool:
    return True  # Password removed — open access


# ── Page ───────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard_new.html")


# ── Login / Logout ─────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    if data.get("password") == DASHBOARD_PASSWORD:
        session["auth"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Wrong password"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


# ── Overview stats ─────────────────────────────────────────────

@app.route("/api/dashboard-data")
def api_dashboard_data():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        counts  = {}
        for r in records:
            s = (((r.get("properties") or {}).get("Status") or {}).get("select") or {}).get("name") or "New"
            counts[s] = counts.get(s, 0) + 1

        emails_sent = (
            counts.get("Contacted",        0) +
            counts.get("Follow-up 1",      0) +
            counts.get("Follow-up Sent",   0) +
            counts.get("Follow-up 1 Sent", 0) +
            counts.get("Replied",          0) +
            counts.get("Closed",           0)
        )
        return jsonify({
            "leads_total":      len(records),
            "emails_sent":      emails_sent,
            "replies_received": counts.get("Replied", 0),
            "new_leads":        counts.get("New",         0),
            "contacted":        counts.get("Contacted",   0),
            "followup_sent":    (counts.get("Follow-up 1", 0) +
                                 counts.get("Follow-up Sent", 0) +
                                 counts.get("Follow-up 1 Sent", 0)),
            "closed":           counts.get("Closed", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Leads table ────────────────────────────────────────────────

@app.route("/api/leads")
def api_leads():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        leads   = [_extract_full_lead(r) for r in records]
        leads.sort(key=lambda x: x["date_added"], reverse=True)
        return jsonify({"leads": leads, "total": len(leads)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Emails log ─────────────────────────────────────────────────

@app.route("/api/emails")
def api_emails():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        emails  = []
        for r in records:
            lead   = _extract_full_lead(r)
            status = lead.get("status", "New")
            if status in ("New", ""):
                continue
            e_type = "Follow-up" if status in ("Follow-up 1", "Follow-up 1 Sent", "Follow-up Sent") else "Cold"
            emails.append({
                "from_account":  lead.get("email_sent_from") or "—",
                "lead_email":    lead["email"],
                "channel_name":  lead["channel_name"],
                "niche":         lead["niche"],
                "sent_at":       lead["last_contact"] or lead["date_added"] or "",
                "email_type":    e_type,
                "status":        status,
            })
        emails.sort(key=lambda x: x["sent_at"], reverse=True)
        return jsonify({"emails": emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Replies log ────────────────────────────────────────────────

@app.route("/api/replies")
def api_replies():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        replies = []
        for r in records:
            lead = _extract_full_lead(r)
            if lead.get("replied"):
                replies.append({
                    "channel_name":      lead["channel_name"],
                    "email":             lead["email"],
                    "reply_time":        lead["reply_date"],
                    "message":           lead["reply_message"],
                    "reply_message":     lead["reply_message"],
                    "status":            "Replied",
                    "sent_from_account": lead.get("email_sent_from") or "—",
                    "niche":             lead.get("niche") or "",
                    "youtube_url":       lead.get("youtube_url") or "",
                })
        replies.sort(key=lambda x: x["reply_time"] or "", reverse=True)
        return jsonify({"replies": replies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Dropdown options ───────────────────────────────────────────

@app.route("/api/niche-options")
def api_niche_options():
    return jsonify({"options": NICHE_OPTIONS})

@app.route("/api/location-options")
def api_location_options():
    return jsonify({"options": list(LOCATION_OPTIONS.keys())})

@app.route("/api/subscriber-range-options")
def api_sub_range_options():
    return jsonify({"options": list(SUBSCRIBER_RANGES.keys())})


# ── Intelligence ───────────────────────────────────────────────

@app.route("/api/niche-health")
def api_niche_health():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        intel = LeadIntelligence()
        return jsonify(intel.get_niche_health())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/expansion-suggestions")
def api_expansion_suggestions():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        intel = LeadIntelligence()
        return jsonify(intel.get_expansion_suggestions())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Scraper — background thread ────────────────────────────────

def _run_scraper(niche: str, location: str, sub_range: str, max_leads: int):
    _log(f"[{_ts()}] ▷ Starting — niche={niche} | loc={location} | range={sub_range} | target={max_leads}")
    with _state_lock:
        _scrape_state.update({"status": "running", "progress": 0, "leads_found": 0, "total": int(max_leads)})

    _ICONS = {"success":"✅","warning":"⚠","error":"❌","info":"  ","progress":"📊","complete":"🏁"}
    try:
        for event in scrape_leads(niche, location, sub_range, max_leads):
            if _stop_event.is_set():
                _log(f"[{_ts()}] ⏹ STOPPED by user")
                with _state_lock: _scrape_state["status"] = "stopped"
                return
            while _pause_event.is_set() and not _stop_event.is_set():
                time.sleep(0.4)
            if _stop_event.is_set():
                _log(f"[{_ts()}] ⏹ STOPPED by user")
                with _state_lock: _scrape_state["status"] = "stopped"
                return
            etype = event.get("type", "info")
            emsg  = event.get("message", "")
            edata = event.get("data", {}) or {}
            _log(f"[{event.get('time', _ts())}] {_ICONS.get(etype,'  ')} {emsg}")
            if etype == "progress" and edata:
                found = edata.get("found", 0)
                target = edata.get("target", int(max_leads))
                with _state_lock:
                    _scrape_state["leads_found"] = found
                    _scrape_state["total"]       = target
                    _scrape_state["progress"]    = int(found / target * 100) if target else 0
            if etype == "complete":
                lf = edata.get("leads_found", _scrape_state["leads_found"])
                with _state_lock:
                    _scrape_state["status"]      = "completed"
                    _scrape_state["progress"]    = 100
                    _scrape_state["leads_found"] = lf
        with _state_lock:
            if _scrape_state["status"] == "running":
                _scrape_state["status"]   = "completed"
                _scrape_state["progress"] = 100
    except Exception as exc:
        _log(f"[{_ts()}] ❌ FATAL ERROR: {exc}")
        with _state_lock: _scrape_state["status"] = "error"


@app.route("/api/start-scrape", methods=["POST"])
def api_start_scrape():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    global _stop_event, _pause_event
    with _state_lock:
        if _scrape_state.get("status") == "running":
            return jsonify({"success": False, "error": "Scraper already running"}), 400
    data      = request.get_json(force=True)
    niche     = data.get("niche", "").strip()
    location  = data.get("location", "").strip()
    sub_range = data.get("sub_range", "").strip()
    max_leads = int(data.get("max_leads", 30))

    # ── RULE 1: Hard limit validation — backend guard ──
    if max_leads > 30:
        return jsonify({"success": False, "error": "Maximum 30 leads per search. Please enter 30 or less."}), 400
    if max_leads < 1:
        return jsonify({"success": False, "error": "Target leads must be at least 1."}), 400

    if not all([niche, location, sub_range]):
        return jsonify({"success": False, "error": "Missing niche, location, or subscriber range"}), 400
    _stop_event  = threading.Event()
    _pause_event = threading.Event()
    t = threading.Thread(target=_run_scraper, args=(niche, location, sub_range, max_leads), daemon=True)
    with _state_lock:
        _scrape_state["thread"] = t
        _scrape_state["logs"]   = []
    t.start()
    return jsonify({"success": True})

@app.route("/api/pause-scrape", methods=["POST"])
def api_pause_scrape():
    if not _auth(): return jsonify({"error": "Unauthorized"}), 401
    _pause_event.set()
    with _state_lock: _scrape_state["status"] = "paused"
    _log(f"[{_ts()}] ⏸ Paused by user")
    return jsonify({"success": True})

@app.route("/api/resume-scrape", methods=["POST"])
def api_resume_scrape():
    if not _auth(): return jsonify({"error": "Unauthorized"}), 401
    _pause_event.clear()
    with _state_lock:
        if _scrape_state["status"] == "paused":
            _scrape_state["status"] = "running"
    _log(f"[{_ts()}] ▶ Resumed")
    return jsonify({"success": True})

@app.route("/api/stop-scrape", methods=["POST"])
def api_stop_scrape():
    if not _auth(): return jsonify({"error": "Unauthorized"}), 401
    _stop_event.set(); _pause_event.clear()
    with _state_lock: _scrape_state["status"] = "stopped"
    _log(f"[{_ts()}] ⏹ Stopped by user")
    return jsonify({"success": True})

@app.route("/api/scrape-status")
def api_scrape_status():
    if not _auth(): return jsonify({"error": "Unauthorized"}), 401
    with _state_lock:
        return jsonify({
            "status":      _scrape_state["status"],
            "progress":    _scrape_state["progress"],
            "leads_found": _scrape_state["leads_found"],
            "total":       _scrape_state["total"],
            "logs":        list(_scrape_state["logs"]),
        })


# ══════════════════════════════════════════════════════════════
# EMAIL ACTION BACKGROUND RUNNERS
# Each runs in a daemon thread; _alog() writes to live log.
# ══════════════════════════════════════════════════════════════

def _run_send_emails():
    """Background: cold email every 'New' lead with fresh YouTube data + Claude."""
    import traceback as _tb
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "send_emails",
            "progress": 0, "total": 0, "logs": [],
        })

    # ── Step 1: connect to Notion ──────────────────────────────
    _alog(f"[{_ts()}]    Step 1: Connecting to Notion…")
    try:
        notion = NotionManager()
    except Exception as e:
        _alog(f"[{_ts()}] ❌ Failed to create NotionManager: {e}")
        _alog(f"[{_ts()}] ❌ {_tb.format_exc()[-400:]}")
        with _email_action_lock:
            _email_action_state["status"] = "error"
        return

    # ── Step 2: fetch all leads ────────────────────────────────
    _alog(f"[{_ts()}]    Step 2: Fetching all leads from Notion…")
    try:
        records = notion.get_all_leads()
        _alog(f"[{_ts()}]    Fetched {len(records)} total records")
    except Exception as e:
        _alog(f"[{_ts()}] ❌ get_all_leads() failed: {e}")
        _alog(f"[{_ts()}] ❌ {_tb.format_exc()[-400:]}")
        with _email_action_lock:
            _email_action_state["status"] = "error"
        return

    # ── Step 3: filter to New leads ────────────────────────────
    _alog(f"[{_ts()}]    Step 3: Filtering for New leads…")
    new_leads = []
    skipped   = 0
    for idx, _r in enumerate(records):
        try:
            if _r is None:
                skipped += 1
                continue
            _props  = (_r.get("properties") or {}) if isinstance(_r, dict) else {}
            _sel    = (_props.get("Status") or {})
            _status = ((_sel.get("select") or {}).get("name") or "New")
            if _status == "New":
                lead = _extract_full_lead(_r)
                new_leads.append(lead)
        except Exception as _fe:
            skipped += 1
            _alog(f"[{_ts()}]    Skip record #{idx}: {_fe}")

    _alog(f"[{_ts()}]    New: {len(new_leads)}  |  Skipped/other: {skipped}")

    if not new_leads:
        _alog(f"[{_ts()}] ✅ No new leads to email — all caught up!")
        with _email_action_lock:
            _email_action_state["status"] = "completed"
        return

    # ── Step 4: send emails ────────────────────────────────────
    total = len(new_leads)
    with _email_action_lock:
        _email_action_state["total"] = total
    _alog(f"[{_ts()}] ▷ Starting — {total} new lead(s) to email")
    reset_expired()  # Clean up old date records

    sent = 0
    for i, lead in enumerate(new_leads, 1):
        if _email_action_stop.is_set():
            _alog(f"[{_ts()}] ⏹ Stopped by user  ({sent}/{total} sent)")
            with _email_action_lock:
                _email_action_state["status"] = "stopped"
            return

        try:
            email = lead.get("email") or ""
            cname = lead.get("channel_name") or "Unknown"
        except Exception:
            _alog(f"[{_ts()}] ⚠  [{i}/{total}] Malformed lead dict — skip")
            continue

        if not email:
            _alog(f"[{_ts()}] ⚠  [{i}/{total}] Skip {cname} — no email address")
            continue

        # ── Fetch YouTube data ────────────────────────────
        _alog(f"[{_ts()}]    [{i}/{total}] {cname} — fetching YouTube data…")
        try:
            channel_data, videos = _fetch_youtube_for_lead(lead.get("youtube_url") or "")
        except Exception:
            channel_data, videos = {}, []

        merged = {
            "channel_name":     (channel_data.get("channel_name") or cname) if channel_data else cname,
            "niche":            lead.get("niche") or "content creation",
            "subscriber_count": (channel_data.get("subscriber_count") or lead.get("subscriber_count") or 0) if channel_data else (lead.get("subscriber_count") or 0),
            "days_since_upload": days_since_last_video(videos),
        }

        # ── Claude writes email ───────────────────────────
        _alog(f"[{_ts()}]    [{i}/{total}] {cname} — Claude writing email…")
        claude_failed = False
        try:
            subject, body = write_personalized_initial_email(merged, videos)
        except Exception:
            claude_failed = True
            n       = merged["channel_name"]
            subject = f"{n} — Free video edit (no strings)"
            body    = (
                f"Quick one — I run Fuelvia, a video editing agency.\n\n"
                f"We'd like to edit ONE of {n}'s videos completely free. "
                f"No credit card, no strings. You keep the video either way.\n\n"
                f"Reply \"I'm in\" and I'll send a secure upload link.\n\n"
                f"- {SENDER_NAME}\nFounder, Fuelvia\nfuelviaa.com"
            )

        if claude_failed:
            _alog(f"[{_ts()}] ⚠  WARNING: Claude API failed — fallback template used for {cname}")

        # ── Send ──────────────────────────────────────────
        account = _next_account()

        # ── Check daily limit (40/account/day) ──
        if not has_room_today(account["email"]):
            _alog(f"[{_ts()}] 🛑 Daily limit reached for {account['email']} — pausing at {sent}/{total} sent")
            _alog(f"[{_ts()}] Resume tomorrow for the remaining {total - sent} leads")
            with _email_action_lock:
                _email_action_state["status"] = "completed"
            return

        _alog(f"[{_ts()}]    [{i}/{total}] Sending to {email} via {account['email']}…")
        ok = _smtp_send(account, email, subject, body)

        if ok:
            # ── Status update FIRST — this is the critical guard ──
            try:
                notion.update_lead_status(lead["id"], "Contacted")
            except Exception as ne:
                _alog(f"[{_ts()}] ❌ CRITICAL: Status update failed for {cname}: {ne} — preventing double-email")

            # ── Save email body ──
            try:
                notion.save_day1_email_body(lead["id"], body)
            except Exception as ne:
                _alog(f"[{_ts()}] ⚠  Could not save email body for {cname}: {ne}")

            # ── Save which account sent it ──
            try:
                notion.update_email_sent_from(lead["id"], account["email"])
            except Exception as ne:
                _alog(f"[{_ts()}] ⚠  Could not save sender account for {cname}: {ne}")

            sent += 1
            # ── Increment daily limit counter ──
            increment_today_count(account["email"])
            with _email_action_lock:
                _email_action_state["progress"] = int(sent / total * 100)
            _alog(f"[{_ts()}] ✅ Sent [{sent}/{total}]: {cname} → {email}")
            _alog(f"[{_ts()}] ✅ Notion updated: Status=Contacted, Email Body saved, Sender account saved")

            if i < total and not _email_action_stop.is_set():
                remaining = total - sent
                next_account = _peek_next_account()
                _alog(f"[{_ts()}] ⏳ WAITING 2 MINUTES before next email...")
                _alog(f"[{_ts()}]    Next: {remaining} leads remaining")
                _alog(f"[{_ts()}]    Next account: {next_account['email']}")
                _alog(f"[{_ts()}]    Starting to write next email during wait time...")

                # Wait 2 minutes (120 seconds) with ability to stop
                wait_secs = EMAIL_ROTATION_DELAY
                wait_ticks = wait_secs * 2  # Each tick is 0.5 seconds
                for tick in range(wait_ticks):
                    if _email_action_stop.is_set():
                        _alog(f"[{_ts()}] ⏹ Stopped during cooldown")
                        break
                    # Show progress every 30 seconds
                    if tick % 60 == 0 and tick > 0:
                        elapsed = tick // 2
                        remaining_wait = wait_secs - elapsed
                        _alog(f"[{_ts()}]    {remaining_wait}s remaining...")
                    time.sleep(0.5)
                _alog(f"[{_ts()}] ✅ 2-minute cooldown complete — ready to send next email")
        else:
            _alog(f"[{_ts()}] ❌ SMTP failed for {email}")

    _alog(f"[{_ts()}] 🏁 Done!  {sent}/{total} cold emails sent.")
    with _email_action_lock:
        _email_action_state.update({"status": "completed", "progress": 100})


def _run_send_followup():
    """Background: follow-up every 'Contacted' lead using saved Day 1 body."""
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "send_followup",
            "progress": 0, "total": 0, "logs": [],
        })
    reset_expired()  # Clean up old date records

    try:
        notion  = NotionManager()
        records = notion.get_all_contacted_leads()

        if not records:
            _alog(f"[{_ts()}] ✅ No contacted leads to follow up — all done!")
            with _email_action_lock:
                _email_action_state["status"] = "completed"
            return

        total = len(records)
        with _email_action_lock:
            _email_action_state["total"] = total
        _alog(f"[{_ts()}] ▷ Starting — {total} contacted lead(s) to follow up")

        sent = 0
        for i, r in enumerate(records, 1):
            if _email_action_stop.is_set():
                _alog(f"[{_ts()}] ⏹ Stopped by user  ({sent}/{total} sent)")
                with _email_action_lock:
                    _email_action_state["status"] = "stopped"
                return

            lead  = _extract_full_lead(r)
            email = lead.get("email", "")
            cname = lead.get("channel_name", "Unknown")

            if not email:
                _alog(f"[{_ts()}] ⚠  [{i}/{total}] Skip {cname} — no email address")
                continue

            if lead.get("day2_sent", False):
                _alog(f"[{_ts()}] ⚠  [{i}/{total}] Skip {cname} — follow-up already sent")
                continue

            # ── Claude writes follow-up from Day 1 body ───────
            day1_body = lead.get("day1_email_body", "")
            _alog(f"[{_ts()}]    [{i}/{total}] {cname} — Claude writing follow-up…")
            try:
                subject, body = write_personalized_followup_1(
                    {
                        "channel_name":    cname,
                        "niche":           lead.get("niche", "content creation"),
                        "subscriber_count": lead.get("subscriber_count", 0),
                    },
                    day1_email_body=day1_body,
                )
            except Exception:
                subject = f"Re: {cname}"
                body    = (
                    f"Just circling back on the free edit offer for {cname} — "
                    f"still happy to take one of your raw videos and edit it completely free.\n\n"
                    f"Reply \"I'm in\" if you want to give it a shot.\n\n"
                    f"– {SENDER_NAME}, Fuelvia"
                )

            # ── Send from SAME account as cold email ──────────
            sent_from = lead.get("email_sent_from", "")
            account   = None
            for acc in OUTREACH_ACCOUNTS:
                if acc["email"].lower() == sent_from.lower():
                    account = acc
                    break

            if not account:
                if not sent_from or sent_from.strip() == "":
                    _alog(f"[{_ts()}] ❌ [{i}/{total}] SKIP {cname} — Email Sent From is BLANK (cold email may have failed)")
                else:
                    _alog(f"[{_ts()}] ⚠  [{i}/{total}] Skip {cname} — no matching account for '{sent_from}'")
                continue

            # ── Check daily limit (40/account/day) ──
            if not has_room_today(account["email"]):
                _alog(f"[{_ts()}] 🛑 Daily limit reached for {account['email']} — pausing at {sent}/{total} sent")
                _alog(f"[{_ts()}] Resume tomorrow for the remaining {total - sent} follow-ups")
                with _email_action_lock:
                    _email_action_state["status"] = "completed"
                return

            _alog(f"[{_ts()}]    [{i}/{total}] Sending follow-up to {email} via {account['email']}…")
            ok = _smtp_send(account, email, subject, body)

            if ok:
                notion.mark_followup1_sent(lead["id"])
                sent += 1
                # ── Increment daily limit counter ──
                increment_today_count(account["email"])
                with _email_action_lock:
                    _email_action_state["progress"] = int(sent / total * 100)
                _alog(f"[{_ts()}] ✅ Follow-up sent [{sent}/{total}]: {cname}")
                _alog(f"[{_ts()}] ✅ Notion updated: Day 2 Sent = True, Status = Follow-up 1")

                if i < total and not _email_action_stop.is_set():
                    remaining = total - sent
                    _alog(f"[{_ts()}] ⏳ WAITING 2 MINUTES before next follow-up...")
                    _alog(f"[{_ts()}]    {remaining} follow-ups remaining")

                    # Wait 2 minutes (120 seconds) with ability to stop
                    wait_secs = EMAIL_ROTATION_DELAY
                    wait_ticks = wait_secs * 2  # Each tick is 0.5 seconds
                    for tick in range(wait_ticks):
                        if _email_action_stop.is_set():
                            _alog(f"[{_ts()}] ⏹ Stopped during cooldown")
                            break
                        # Show progress every 30 seconds
                        if tick % 60 == 0 and tick > 0:
                            elapsed = tick // 2
                            remaining_wait = wait_secs - elapsed
                            _alog(f"[{_ts()}]    {remaining_wait}s remaining...")
                        time.sleep(0.5)
                    _alog(f"[{_ts()}] ✅ 2-minute cooldown complete — ready to send next follow-up")
            else:
                _alog(f"[{_ts()}] ❌ SMTP failed for {email}")

        _alog(f"[{_ts()}] 🏁 Done!  {sent}/{total} follow-ups sent.")
        with _email_action_lock:
            _email_action_state.update({"status": "completed", "progress": 100})

    except Exception as e:
        _alog(f"[{_ts()}] ❌ Fatal error: {str(e)[:200]}")
        with _email_action_lock:
            _email_action_state["status"] = "error"


def _run_check_replies():
    """Background: scan all IMAP inboxes for replies, save to Notion."""
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "check_replies",
            "progress": 0, "total": 0, "logs": [],
        })

    try:
        notion  = NotionManager()
        records = notion.get_all_leads()

        emails_map, refresh_map = {}, {}
        for r in records:
            lead = _extract_full_lead(r)
            e    = lead.get("email", "").lower()
            if not e:
                continue
            if not lead.get("replied", False):
                emails_map[e] = lead
            elif len(lead.get("reply_message", "")) < 80:
                refresh_map[e] = lead

        _alog(f"[{_ts()}] ▷ Scanning {len(OUTREACH_ACCOUNTS)} accounts for replies")
        _alog(f"[{_ts()}]   Watching {len(emails_map)} leads · refreshing {len(refresh_map)} short bodies")

        if not emails_map and not refresh_map:
            _alog(f"[{_ts()}] ✅ All leads already marked as replied")
            with _email_action_lock:
                _email_action_state["status"] = "completed"
            return

        replies_found = {}
        since_date    = (date.today() - timedelta(days=30)).strftime("%d-%b-%Y")

        for acc_idx, account in enumerate(OUTREACH_ACCOUNTS):
            if _email_action_stop.is_set():
                break

            _alog(f"[{_ts()}]    Connecting to {account['email']}…")
            try:
                mail = imaplib.IMAP4_SSL(account.get("imap_server", "imap.gmail.com"), timeout=30)
                mail.login(account["email"], account["password"])
                mail.select("INBOX")

                _, data = mail.search(None, f'SINCE {since_date}')
                email_ids = data[0].split() if data[0] else []
                _alog(f"[{_ts()}]    {account['email']}: {len(email_ids)} emails in last 30 days")

                if not email_ids:
                    mail.logout()
                    with _email_action_lock:
                        _email_action_state["progress"] = int((acc_idx + 1) / len(OUTREACH_ACCOUNTS) * 60)
                    continue

                # Batch fetch headers (1 IMAP round-trip)
                ids_str = b",".join(email_ids).decode()
                _, hdr_data_all = mail.fetch(ids_str, "(BODY.PEEK[HEADER])")

                hdr_pairs = []
                for item in (hdr_data_all or []):
                    if isinstance(item, tuple) and len(item) == 2:
                        try:
                            meta    = item[0].decode(errors="replace")
                            msg_num = meta.split()[0]
                            hdr_pairs.append((msg_num, item[1]))
                        except Exception:
                            pass

                all_targets = {**emails_map, **refresh_map}
                for msg_num, raw_hdr in hdr_pairs:
                    try:
                        if not raw_hdr:
                            continue
                        hdr_msg = _email_lib.message_from_bytes(raw_hdr)
                        subj    = hdr_msg.get("Subject", "") or ""
                        is_reply = (
                            subj.lower().startswith("re:") or
                            bool(hdr_msg.get("In-Reply-To")) or
                            bool(hdr_msg.get("References"))
                        )
                        if not is_reply:
                            continue
                        _, from_email = parseaddr(hdr_msg.get("From", ""))
                        from_email = from_email.lower()
                        if from_email not in all_targets or from_email in replies_found:
                            continue

                        # Full body fetch only for matches
                        _, msg_data = mail.fetch(msg_num, "(RFC822)")
                        if not msg_data or not msg_data[0]:
                            continue
                        raw_msg = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                        if not raw_msg:
                            continue
                        full_msg  = _email_lib.message_from_bytes(raw_msg)
                        body_text = _extract_email_body(full_msg)
                        iso_date  = _parse_email_date(hdr_msg.get("Date", ""))

                        replies_found[from_email] = {
                            "email":        from_email,
                            "reply_time":   iso_date,
                            "full_message": body_text,
                            "is_refresh":   from_email in refresh_map,
                        }
                        kind = "REFRESH" if from_email in refresh_map else "NEW REPLY"
                        _alog(f"[{_ts()}] ✅ {kind}: {from_email} ({len(body_text)} chars)")
                    except Exception:
                        continue

                mail.logout()
                with _email_action_lock:
                    _email_action_state["progress"] = int((acc_idx + 1) / len(OUTREACH_ACCOUNTS) * 60)

            except Exception as e:
                _alog(f"[{_ts()}] ❌ IMAP error ({account['email']}): {str(e)[:100]}")

        # Save to Notion
        saved   = 0
        refresh = 0
        total_r = len(replies_found)
        if total_r:
            _alog(f"[{_ts()}]    Saving {total_r} reply(ies) to Notion…")

        for ri, reply in enumerate(replies_found.values(), 1):
            try:
                if reply.get("is_refresh"):
                    res = notion.update_reply_message(reply["email"], reply.get("full_message", ""))
                    if res is not None:
                        refresh += 1
                        _alog(f"[{_ts()}]    Body refreshed: {reply['email']}")
                else:
                    res = notion.mark_replied(
                        reply["email"],
                        reply_message=reply.get("full_message", ""),
                        reply_time=reply.get("reply_time"),
                    )
                    if res is not None:
                        saved += 1
                        _alog(f"[{_ts()}]    Marked replied: {reply['email']}")
                with _email_action_lock:
                    _email_action_state["progress"] = 60 + int(ri / max(total_r, 1) * 40)
            except Exception as ne:
                _alog(f"[{_ts()}] ❌ Notion error ({reply['email']}): {str(ne)[:100]}")

        parts = []
        if saved:   parts.append(f"{saved} new reply(ies) saved")
        if refresh: parts.append(f"{refresh} body(ies) refreshed")
        summary = ", ".join(parts) if parts else "No new replies found"
        _alog(f"[{_ts()}] 🏁 {summary}")
        with _email_action_lock:
            _email_action_state.update({"status": "completed", "progress": 100})

    except Exception as e:
        _alog(f"[{_ts()}] ❌ Fatal error: {str(e)[:200]}")
        with _email_action_lock:
            _email_action_state["status"] = "error"


# ── Email action API endpoints ─────────────────────────────────

def _start_action(target_fn, name: str):
    """Helper: reject if busy, else start background thread."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    with _email_action_lock:
        if _email_action_state.get("status") == "running":
            action = _email_action_state.get("action", "?")
            return jsonify({"error": f"Action already running: {action}"}), 400
    t = threading.Thread(target=target_fn, daemon=True, name=f"fuelvia-{name}")
    t.start()
    return jsonify({"success": True})


@app.route("/api/send-emails", methods=["POST"])
def api_send_emails():
    return _start_action(_run_send_emails, "send-emails")


@app.route("/api/send-followup", methods=["POST"])
def api_send_followup():
    return _start_action(_run_send_followup, "send-followup")


@app.route("/api/check-replies", methods=["POST"])
def api_check_replies():
    return _start_action(_run_check_replies, "check-replies")


@app.route("/api/email-action-status")
def api_email_action_status():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    with _email_action_lock:
        return jsonify({
            "status":   _email_action_state["status"],
            "action":   _email_action_state["action"],
            "progress": _email_action_state["progress"],
            "total":    _email_action_state["total"],
            "logs":     list(_email_action_state["logs"]),
        })


@app.route("/api/stop-email-action", methods=["POST"])
def api_stop_email_action():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    _email_action_stop.set()
    with _email_action_lock:
        _email_action_state["status"] = "stopped"
    return jsonify({"success": True})


# ── Admin remote update ────────────────────────────────────────

@app.route("/admin/change", methods=["POST"])
def admin_change():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {ADMIN_KEY}":
        return jsonify({"error": "Unauthorized"}), 401
    data        = request.get_json(force=True)
    change_type = data.get("type", "")
    if change_type == "emails":
        new_accounts = (data.get("data") or {}).get("accounts", [])
        if new_accounts:
            OUTREACH_ACCOUNTS.clear()
            OUTREACH_ACCOUNTS.extend(new_accounts)
            return jsonify({"success": True, "message": f"Updated {len(new_accounts)} outreach account(s)"})
    if change_type == "password":
        global DASHBOARD_PASSWORD
        new_pw = (data.get("data") or {}).get("password", "")
        if new_pw:
            DASHBOARD_PASSWORD = new_pw
            return jsonify({"success": True, "message": "Password updated"})
    return jsonify({"success": False, "error": f"Unknown change type: {change_type}"}), 400


# ── Export CSV ────────────────────────────────────────────────

@app.route("/api/export-csv")
def api_export_csv():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        import csv
        import io as _sio
        notion  = NotionManager()
        records = notion.get_all_leads()
        leads   = [_extract_full_lead(r) for r in records]
        leads.sort(key=lambda x: x["date_added"], reverse=True)
        output = _sio.StringIO()
        fields = [
            "channel_name", "email", "subscriber_count", "niche", "location",
            "score", "status", "replied", "email_sent_from", "date_added",
            "last_contact", "reply_date", "reply_message", "notes", "youtube_url",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)
        return Response(
            output.getvalue().encode("utf-8"),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=fuelvia-leads.csv"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Analytics chart data ───────────────────────────────────────

@app.route("/api/analytics-data")
def api_analytics_data():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        emails_by_day  = {}
        replies_by_day = {}
        for r in records:
            lead = _extract_full_lead(r)
            # Emails: group by last_contact date
            contact_d = (lead.get("last_contact") or "").split("T")[0]
            if contact_d and lead.get("status") not in ("New", ""):
                emails_by_day[contact_d] = emails_by_day.get(contact_d, 0) + 1
            # Replies: group by reply_date
            reply_d = (lead.get("reply_date") or "").split("T")[0]
            if reply_d:
                replies_by_day[reply_d] = replies_by_day.get(reply_d, 0) + 1
        # Fill with last 14 days if no data
        all_dates = sorted(set(list(emails_by_day.keys()) + list(replies_by_day.keys())))
        if not all_dates:
            all_dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        labels      = all_dates[-30:]
        emails_data = [emails_by_day.get(d, 0)  for d in labels]
        replies_data= [replies_by_day.get(d, 0) for d in labels]
        return jsonify({"labels": labels, "emails": emails_data, "replies": replies_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI Email Preview ───────────────────────────────────────────

@app.route("/api/preview-email", methods=["POST"])
def api_preview_email():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data    = request.get_json(force=True)
        lead_id = data.get("lead_id", "")
        notion  = NotionManager()
        records = notion.get_all_leads()
        lead    = None
        for r in records:
            if r.get("id") == lead_id:
                lead = _extract_full_lead(r)
                break
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        channel_data, videos = _fetch_youtube_for_lead(lead.get("youtube_url") or "")
        merged = {
            "channel_name":     (channel_data.get("channel_name") or lead.get("channel_name") or "Unknown") if channel_data else (lead.get("channel_name") or "Unknown"),
            "niche":            lead.get("niche") or "content creation",
            "subscriber_count": (channel_data.get("subscriber_count") or lead.get("subscriber_count") or 0) if channel_data else (lead.get("subscriber_count") or 0),
            "days_since_upload": days_since_last_video(videos),
        }
        used_claude = False
        try:
            subject, body = write_personalized_initial_email(merged, videos)
            used_claude = True
        except Exception:
            n = merged["channel_name"]
            subject = f"{n} — Free video edit (no strings)"
            body = (
                f"Quick one — I run Fuelvia, a video editing agency.\n\n"
                f"We'd like to edit ONE of {n}'s videos completely free. "
                f"No credit card, no strings. You keep the video either way.\n\n"
                f"Reply \"I'm in\" and I'll send a secure upload link.\n\n"
                f"- {SENDER_NAME}\nFounder, Fuelvia\nfuelviaa.com"
            )
        return jsonify({
            "subject":      subject,
            "body":         body,
            "channel_name": merged["channel_name"],
            "used_claude":  used_claude,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Campaign History ───────────────────────────────────────────

@app.route("/api/campaign-history")
def api_campaign_history():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        by_date = {}
        for r in records:
            lead = _extract_full_lead(r)
            contact_d = (lead.get("last_contact") or "").split("T")[0]
            if not contact_d or lead.get("status") in ("New", ""):
                continue
            if contact_d not in by_date:
                by_date[contact_d] = {"date": contact_d, "emails": 0, "followups": 0, "replies": 0, "niches": set(), "accounts": set()}
            by_date[contact_d]["emails"] += 1
            s = lead.get("status", "")
            if "Follow-up" in s:
                by_date[contact_d]["followups"] += 1
            if s == "Replied":
                by_date[contact_d]["replies"] += 1
            if lead.get("niche"):
                by_date[contact_d]["niches"].add(lead["niche"])
            if lead.get("email_sent_from"):
                by_date[contact_d]["accounts"].add(lead["email_sent_from"])
        campaigns = []
        for d, c in sorted(by_date.items(), reverse=True):
            campaigns.append({
                "date":       d,
                "emails":     c["emails"],
                "followups":  c["followups"],
                "replies":    c["replies"],
                "reply_rate": round(c["replies"] / c["emails"] * 100, 1) if c["emails"] else 0,
                "niches":     list(c["niches"]),
                "accounts":   list(c["accounts"]),
            })
        return jsonify({"campaigns": campaigns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    from config import YOUTUBE_APIS as _YT_KEYS
    print("\n" + "=" * 52)
    print(f"  [OK] {len(_YT_KEYS)} YouTube API key(s) loaded - rotation enabled")
    print("\n" + "=" * 52)
    print("  FUELVIA Lead Generation Dashboard")
    print("  Open:     http://127.0.0.1:5000")
    print("  Password: fuelvia2025")
    print("=" * 52 + "\n")
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
