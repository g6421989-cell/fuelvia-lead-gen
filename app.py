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
    SENDER_NAME, COMPANY_NAME,
)
from notion_manager import NotionManager
from claude_helpers import write_personalized_initial_email, write_personalized_followup_1
from youtube_enricher import get_videos_for_channel, days_since_last_video
from lead_intelligence import LeadIntelligence
from scraper_engine import scrape_leads
from daily_send_limit import has_room_today, increment_today_count, reset_expired
import settings_store


# ── App setup ──────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "fuelvia-secret-2026"

DASHBOARD_PASSWORD = "fuelvia2025"
ADMIN_KEY          = "FuelVia_Admin_2026_SecureRemote_Key_xyz789abc123def"


# ── Load email config (3-tier fallback) ───────────────────────────────────────
def _load_email_config():
    """
    Load outreach accounts in priority order:
      1. EMAIL_CONFIG env var (JSON string) — for Render/cloud deployment
      2. email_config.json file             — for local development
      3. OUTREACH_ACCOUNTS in config.py     — hardcoded fallback (always works)
    """
    # Tier 1: env var
    email_config_env = os.getenv("EMAIL_CONFIG")
    if email_config_env:
        try:
            cfg = json.loads(email_config_env)
            accts = cfg.get("outreach_emails", [])
            if accts:
                print(f"[OK] Email accounts loaded from EMAIL_CONFIG env var ({len(accts)})")
                return accts
        except Exception as e:
            print(f"WARNING: Could not parse EMAIL_CONFIG env var: {e}")

    # Tier 2: JSON file
    config_path = os.path.join(os.path.dirname(__file__), "email_config.json")
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        accts = cfg.get("outreach_emails", [])
        if accts:
            print(f"[OK] Email accounts loaded from email_config.json ({len(accts)})")
            return accts
    except Exception:
        pass  # file not present — try next tier

    # Tier 3: hardcoded in config.py (always available, even on Render)
    try:
        from config import OUTREACH_ACCOUNTS as _cfg_accts
        if _cfg_accts:
            print(f"[OK] Email accounts loaded from config.py ({len(_cfg_accts)})")
            return list(_cfg_accts)
    except Exception as e:
        print(f"WARNING: Could not load accounts from config.py: {e}")

    print("WARNING: No outreach accounts found in any source")
    return []

OUTREACH_ACCOUNTS = _load_email_config()
if OUTREACH_ACCOUNTS:
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

# Holds the result of the most recent "Qualify Leads" PREVIEW so the
# follow-up "Apply Cleanup" step archives exactly the leads you reviewed.
_qualify_state = {"cut_ids": [], "cut_preview": [], "summary": {}, "preview_at": None}
_qualify_lock  = threading.Lock()


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


def _smtp_send(account: dict, to_email: str, subject: str, body: str) -> tuple:
    """
    Returns (success: bool, error_msg: str).
    Tries STARTTLS on configured port first, then falls back to SSL on port 465.
    This handles cloud platforms (like Render) that block port 587.
    """
    msg = MIMEMultipart()
    founder_name = _get_founder_name(account["email"])
    msg["From"]    = f"{founder_name} - {COMPANY_NAME} <{account['email']}>"
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = msg.as_string()

    errors = []

    # ── Attempt 1: STARTTLS on configured port (587) ──────────────
    try:
        with smtplib.SMTP(account["smtp_server"], account["smtp_port"], timeout=30) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(account["email"], account["password"])
            srv.sendmail(account["email"], to_email, raw)
        return True, ""
    except Exception as e:
        errors.append(f"STARTTLS port {account['smtp_port']}: {e}")

    # ── Attempt 2: SSL on port 465 (Render / cloud fallback) ──────
    ssl_port = 465
    if account["smtp_port"] != ssl_port:
        try:
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            with smtplib.SMTP_SSL(account["smtp_server"], ssl_port, timeout=30, context=ctx) as srv:
                srv.login(account["email"], account["password"])
                srv.sendmail(account["email"], to_email, raw)
            return True, ""
        except Exception as e:
            errors.append(f"SSL port {ssl_port}: {e}")

    err = " | ".join(errors)
    print(f"  [SMTP] All send attempts failed for {to_email}: {err}")
    return False, err


# ── YouTube re-fetch helper ────────────────────────────────────

_YT_CHANNEL_RE = _re.compile(r'/channel/([A-Za-z0-9_-]{20,})')


def _fetch_youtube_for_lead(youtube_url: str) -> tuple:
    if not youtube_url:
        return {}, []
    m = _YT_CHANNEL_RE.search(youtube_url)
    if not m:
        return {}, []
    channel_id = m.group(1)

    for key in settings_store.get_list("YOUTUBE_API_KEYS"):
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


# ── SECURITY: Bot Detection, Headers, Robots/LLMs ─────────────────────────────

@app.before_request
def security_check():
    """
    ALLOWLIST approach: only real browsers with Mozilla + browser token pass.
    Everything else — AI tools, curl, scrapers, headless browsers — gets decoy.
    API endpoints (/api/*) are exempt from UA check so AJAX still works.
    """
    from security import _is_real_browser, _log_threat, _get_decoy_page

    ip   = request.remote_addr
    ua   = request.headers.get('User-Agent', '')
    path = request.path

    # Honeypot paths — log and serve decoy regardless of UA
    honeypots = ['/admin', '/wp-admin', '/backup', '.env', 'package.json', '.map']
    if any(hp in path for hp in honeypots):
        _log_threat(ip, "honeypot_access", ua)
        return _get_decoy_page(), 200, {'Content-Type': 'text/html'}

    # API calls come from the browser's own JS — skip UA check for them
    if path.startswith('/api/'):
        return

    # Static assets — skip
    if path.startswith('/static/'):
        return

    # Everything else: enforce real-browser UA allowlist
    if not _is_real_browser(ua):
        _log_threat(ip, "non_browser_blocked", ua)
        return _get_decoy_page(), 200, {'Content-Type': 'text/html'}

@app.after_request
def add_sec_headers(response):
    """Add hardening headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers['Server'] = 'nginx'
    if 'X-Powered-By' in response.headers:
        del response.headers['X-Powered-By']
    return response

@app.route('/robots.txt')
def robots():
    """Block all bots via robots.txt."""
    return """User-agent: *
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: GPTBot
Disallow: /

User-agent: anthropic-ai
Disallow: /
""", 200, {'Content-Type': 'text/plain'}

@app.route('/.well-known/llms.txt')
def llms():
    """LLM crawling policy."""
    return "This site does not authorize AI training, analysis, or scraping.", 200, {'Content-Type': 'text/plain'}


# ── Pages ──────────────────────────────────────────────────────

@app.route("/")
def index():
    """Dashboard — password removed, open access (bot-detection decoy still applies)."""
    return render_template("dashboard_new.html")

@app.route("/dashboard")
def dashboard():
    """Dashboard — password removed, served directly."""
    return render_template("dashboard_new.html")


# ── Login / Logout (password removed — kept as no-ops for compatibility) ──

@app.route("/api/login", methods=["POST"])
def api_login():
    # Password removed: always succeed so any legacy client call still works.
    session["auth"] = True
    return jsonify({"success": True, "redirect": "/dashboard"})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def api_me():
    """Password removed — always authenticated."""
    return jsonify({"authenticated": True})


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
            "queued":           counts.get("Queued",      0),
            "contacted":        counts.get("Contacted",   0),
            "followup_sent":    (counts.get("Follow-up 1", 0) +
                                 counts.get("Follow-up Sent", 0) +
                                 counts.get("Follow-up 1 Sent", 0)),
            "closed":           counts.get("Closed", 0),
            "bounced":          counts.get("Bounced", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Settings (UI-editable API keys & tunables) ──────────────────

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        return jsonify({"success": True, "groups": settings_store.get_all_for_ui()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def api_settings_save():
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        updates = request.get_json(force=True) or {}
        changed = settings_store.set_many(updates)
        settings_store.reload()  # ensure cache reflects new file
        return jsonify({"success": True, "changed": changed,
                        "message": f"Saved {len(changed)} setting(s). Changes are live immediately."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings/test", methods=["POST"])
def api_settings_test():
    """Live-test a provider connection with the CURRENT (saved) settings."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401

    provider = (request.get_json(force=True) or {}).get("provider", "")
    try:
        if provider == "claude":
            from claude_helpers import call_claude
            out = call_claude("Reply with the single word: OK", max_tokens=10)
            ok = bool(out) and "ok" in out.lower()
            return jsonify({"success": ok,
                            "message": f"Claude responded: {out!r}" if ok
                                       else "No valid response — check key, base URL & model."})

        if provider == "notion":
            nm = NotionManager()
            recs = nm.get_all_leads()
            return jsonify({"success": True,
                            "message": f"Notion OK — database reachable, {len(recs)} record(s)."})

        if provider == "youtube":
            from scraper_engine import _get_youtube
            yt, _ = _get_youtube(0)
            # cheapest call: 1-unit channels.list on a known channel
            yt.channels().list(part="id", id="UC_x5XG1OV2P6uZZ5FSM9Ttw").execute()
            n = len(settings_store.get_list("YOUTUBE_API_KEYS"))
            return jsonify({"success": True, "message": f"YouTube OK — {n} key(s), API reachable."})

        if provider == "instantly":
            from instantly_helpers import test_instantly
            ok, msg = test_instantly()
            return jsonify({"success": ok, "message": msg})

        return jsonify({"success": False, "message": f"Unknown provider: {provider}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"{provider} test failed: {str(e)[:200]}"})


@app.route("/api/send-mode")
def api_send_mode():
    """Current send mode + readiness — used by the dashboard header badge."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    mode = settings_store.get("SEND_MODE") or "smtp"
    ready = True
    if mode == "instantly":
        from instantly_helpers import instantly_ready
        ready = instantly_ready()
    return jsonify({
        "mode": mode,
        "label": "Instantly.ai" if mode == "instantly" else "Direct SMTP",
        "ready": ready,
    })


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

def _run_scraper(
    niche: str, location: str, sub_range: str, max_leads: int,
    date_filter_days: int = None,
    city_drill_key: str = None,
    use_fresh_keywords: bool = True,
):
    import traceback as _tb
    try:
        _log(f"[{_ts()}] ▷ Starting — niche={niche} | loc={location} | range={sub_range} | target={max_leads}")
        if date_filter_days:
            _log(f"[{_ts()}] 📅 Date filter: last {date_filter_days} days")
        if city_drill_key and city_drill_key != "Disabled":
            _log(f"[{_ts()}] 🏙 City drilling: {city_drill_key}")
        if use_fresh_keywords:
            _log(f"[{_ts()}] 🔄 Smart keyword rotation: ON")

        _yt_keys = settings_store.get_list("YOUTUBE_API_KEYS")
        _log(f"[{_ts()}]    YouTube API keys loaded: {len(_yt_keys)}")
        if not _yt_keys:
            _log(f"[{_ts()}] ❌ NO YOUTUBE API KEYS — add them in Settings")
            with _state_lock: _scrape_state["status"] = "error"
            return

        _ICONS = {"success":"✅","warning":"⚠","error":"❌","info":"  ","progress":"📊","complete":"🏁"}
        for event in scrape_leads(
            niche, location, sub_range, max_leads,
            date_filter_days=date_filter_days,
            city_drill_key=city_drill_key,
            use_fresh_keywords=use_fresh_keywords,
        ):
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
        tb = _tb.format_exc()
        _log(f"[{_ts()}] ❌ FATAL ERROR: {exc}")
        _log(f"[{_ts()}] ❌ Traceback: {tb[-600:]}")
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

    # v4 fresh-lead params
    date_filter_days  = data.get("date_filter_days")   # int or None
    city_drill_key    = data.get("city_drill_key", "Disabled")
    use_fresh_keywords = bool(data.get("use_fresh_keywords", True))
    if date_filter_days is not None:
        try:
            date_filter_days = int(date_filter_days)
        except (ValueError, TypeError):
            date_filter_days = None

    # ── RULE 1: Hard limit validation — backend guard ──
    if max_leads > 30:
        return jsonify({"success": False, "error": "Maximum 30 leads per search. Please enter 30 or less."}), 400
    if max_leads < 1:
        return jsonify({"success": False, "error": "Target leads must be at least 1."}), 400

    if not all([niche, location, sub_range]):
        return jsonify({"success": False, "error": "Missing niche, location, or subscriber range"}), 400
    _stop_event  = threading.Event()
    _pause_event = threading.Event()
    t = threading.Thread(
        target=_run_scraper,
        args=(niche, location, sub_range, max_leads),
        kwargs={
            "date_filter_days":  date_filter_days,
            "city_drill_key":    city_drill_key,
            "use_fresh_keywords": use_fresh_keywords,
        },
        daemon=True,
    )
    with _state_lock:
        _scrape_state["thread"]     = t
        _scrape_state["logs"]       = []
        _scrape_state["status"]     = "running"   # set BEFORE thread starts so UI is instant
        _scrape_state["progress"]   = 0
        _scrape_state["leads_found"] = 0
        _scrape_state["total"]      = max_leads
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


@app.route("/api/health")
def api_health():
    """System health page — open in browser to verify all config is set correctly."""
    import traceback as _tb
    checks = []

    def row(label, ok, detail=""):
        icon = "✅" if ok else "❌"
        return f"<tr><td>{icon}</td><td><b>{label}</b></td><td style='color:#888'>{detail}</td></tr>"

    # YouTube API keys (LIVE from settings store)
    try:
        _yt = settings_store.get_list("YOUTUBE_API_KEYS")
        n = len(_yt)
        checks.append(row("YouTube API Keys", n > 0,
            f"{n} key(s) loaded" if n > 0 else "MISSING — add in Settings"))
    except Exception as e:
        checks.append(row("YouTube API Keys", False, str(e)))

    # Notion (LIVE)
    try:
        _nk = settings_store.get("NOTION_API_KEY")
        _nd = settings_store.get("NOTION_DATABASE_ID")
        checks.append(row("Notion API Key",     bool(_nk), "set ✓" if _nk else "MISSING"))
        checks.append(row("Notion Database ID", bool(_nd), "set ✓" if _nd else "MISSING"))
    except Exception as e:
        checks.append(row("Notion", False, str(e)))

    # Claude (LIVE)
    try:
        _ck = settings_store.get("CLAUDE_API_KEY")
        checks.append(row("Claude API Key", bool(_ck), "set ✓" if _ck else "MISSING (email still uses fallback templates)"))
    except Exception as e:
        checks.append(row("Claude API Key", False, str(e)))

    # Email accounts
    checks.append(row("Email Accounts", len(OUTREACH_ACCOUNTS) > 0,
        f"{len(OUTREACH_ACCOUNTS)} account(s) loaded" if OUTREACH_ACCOUNTS
        else "MISSING — add EMAIL_CONFIG env var or email_config.json"))

    # Imports
    for mod in ["scraper_engine", "search_tokens", "notion_manager",
                "channel_qualifier", "channel_blacklist", "daily_send_limit"]:
        try:
            __import__(mod)
            checks.append(row(f"import {mod}", True, "OK"))
        except Exception as e:
            checks.append(row(f"import {mod}", False, _tb.format_exc()[-200:]))

    rows_html = "\n".join(checks)
    html = f"""<!DOCTYPE html><html><head><title>Fuelvia Health</title>
<style>body{{font-family:monospace;background:#0a0a0a;color:#d4d4d4;padding:40px}}
table{{border-collapse:collapse;width:600px}}td{{padding:8px 12px;border-bottom:1px solid #222}}
h1{{color:#fff;margin-bottom:24px}}</style></head><body>
<h1>🔧 Fuelvia System Health</h1>
<table>{rows_html}</table>
<p style="margin-top:24px;color:#555;font-size:12px">Scrape status: {_scrape_state.get('status','idle')} &nbsp;|&nbsp;
Email accounts: {len(OUTREACH_ACCOUNTS)}</p>
</body></html>"""
    return html, 200, {"Content-Type": "text/html"}


# ══════════════════════════════════════════════════════════════
# EMAIL ACTION BACKGROUND RUNNERS
# Each runs in a daemon thread; _alog() writes to live log.
# ══════════════════════════════════════════════════════════════

def _run_send_emails(limit=None):
    """Background: cold email 'New' leads with fresh YouTube data + Claude.
    limit = max number of leads to email this run (None = all)."""
    import traceback as _tb
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "send_emails",
            "progress": 0, "total": 0, "logs": [],
        })

    # ── Guard: email accounts must be configured ──────────────
    if not OUTREACH_ACCOUNTS:
        _alog(f"[{_ts()}] ❌ No outreach accounts loaded. Add email_config.json or EMAIL_CONFIG env var.")
        with _email_action_lock:
            _email_action_state["status"] = "error"
        return

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

    # ── Apply user-selected limit (e.g. send only 10 of 50) ────
    _available = len(new_leads)
    if limit and limit > 0 and limit < _available:
        new_leads = new_leads[:limit]
        _alog(f"[{_ts()}]    Limit: sending {limit} of {_available} pending cold emails")

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

        # ── SEND MODE: Instantly.ai (push lead) vs Direct SMTP (below) ──
        # Direct SMTP code is left completely untouched; in Instantly mode we
        # push the lead + personalization to the campaign and skip SMTP.
        if settings_store.get("SEND_MODE") == "instantly":
            from instantly_helpers import add_lead_to_instantly
            _alog(f"[{_ts()}]    [{i}/{total}] {cname} — adding to Instantly campaign…")
            iok, ierr = add_lead_to_instantly(
                email=email,
                channel_name=cname,
                youtube_url=lead.get("youtube_url") or "",
                email_body=body,
                subscriber_count=merged.get("subscriber_count", 0),
                niche=merged.get("niche", ""),
            )
            if iok:
                # Lead is QUEUED in Instantly (not sent yet). "Sync from Instantly"
                # later flips it to Contacted/Replied/Bounced based on real state.
                try:
                    notion.update_lead_status(lead["id"], "Queued")
                except Exception as ne:
                    _alog(f"[{_ts()}] ❌ CRITICAL: Status update failed for {cname}: {ne}")
                try:
                    notion.save_day1_email_body(lead["id"], body)
                except Exception as ne:
                    _alog(f"[{_ts()}] ⚠  Could not save email body for {cname}: {ne}")
                sent += 1
                with _email_action_lock:
                    _email_action_state["progress"] = int(sent / total * 100)
                _alog(f"[{_ts()}] ✅ Queued in Instantly [{sent}/{total}]: {cname} → {email}")
            else:
                _alog(f"[{_ts()}] ❌ Instantly failed for {cname} ({email}): {ierr}")

            # small pause to respect Instantly API rate limits (stop-aware)
            if i < total and not _email_action_stop.is_set():
                for _ in range(2):
                    if _email_action_stop.is_set():
                        break
                    time.sleep(0.5)
            continue   # skip the Direct SMTP block (left untouched)

        # ── Pick account with room (rotate past full ones) ────
        account = None
        _daily_cap = settings_store.get("MAX_EMAILS_PER_ACCOUNT_PER_DAY")
        for _try in range(len(OUTREACH_ACCOUNTS)):
            candidate = _next_account()
            if has_room_today(candidate["email"], limit=_daily_cap):
                account = candidate
                break
            _alog(f"[{_ts()}]    {candidate['email']} at daily limit — trying next account…")

        if not account:
            _alog(f"[{_ts()}] 🛑 All {len(OUTREACH_ACCOUNTS)} accounts at daily limit ({len(OUTREACH_ACCOUNTS)*40} total/day) — pausing at {sent}/{total} sent")
            _alog(f"[{_ts()}] Resume tomorrow for the remaining {total - sent} leads")
            with _email_action_lock:
                _email_action_state["status"] = "completed"
            return

        _alog(f"[{_ts()}]    [{i}/{total}] Sending to {email} via {account['email']}…")
        ok, smtp_err = _smtp_send(account, email, subject, body)

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

                # Wait between sends (live-editable in Settings) with ability to stop
                wait_secs = settings_store.get("EMAIL_ROTATION_DELAY")
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
            _alog(f"[{_ts()}] ❌ SMTP failed for {email}: {smtp_err}")

    _alog(f"[{_ts()}] 🏁 Done!  {sent}/{total} cold emails sent.")
    with _email_action_lock:
        _email_action_state.update({"status": "completed", "progress": 100})


def _run_send_followup(limit=None):
    """Background: follow-up 'Contacted' leads using saved Day 1 body.
    limit = max number of follow-ups to send this run (None = all)."""
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "send_followup",
            "progress": 0, "total": 0, "logs": [],
        })
    reset_expired()  # Clean up old date records

    # ── Guard: email accounts must be configured ──────────────
    if not OUTREACH_ACCOUNTS:
        _alog(f"[{_ts()}] ❌ No outreach accounts loaded. Add email_config.json or EMAIL_CONFIG env var.")
        with _email_action_lock:
            _email_action_state["status"] = "error"
        return

    try:
        notion  = NotionManager()
        records = notion.get_all_contacted_leads()

        if not records:
            _alog(f"[{_ts()}] ✅ No contacted leads to follow up — all done!")
            with _email_action_lock:
                _email_action_state["status"] = "completed"
            return

        # ── Apply user-selected limit (e.g. send only 10 of 50) ────
        _available = len(records)
        if limit and limit > 0 and limit < _available:
            records = records[:limit]
            _alog(f"[{_ts()}]    Limit: sending {limit} of {_available} pending follow-ups")

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

            # ── Check daily limit — follow-ups must use SAME account so no rotation here ──
            if not has_room_today(account["email"], limit=settings_store.get("MAX_EMAILS_PER_ACCOUNT_PER_DAY")):
                _alog(f"[{_ts()}] 🛑 [{i}/{total}] Daily limit reached for {account['email']} — skipping {cname} (will retry tomorrow)")
                continue   # skip this lead today; don't abort the whole run

            _alog(f"[{_ts()}]    [{i}/{total}] Sending follow-up to {email} via {account['email']}…")
            ok, smtp_err = _smtp_send(account, email, subject, body)

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

                    # Wait the configured delay (live from Settings) with ability to stop
                    wait_secs = settings_store.get("EMAIL_ROTATION_DELAY")
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
                _alog(f"[{_ts()}] ❌ SMTP failed for {email}: {smtp_err}")

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
                imap_host = account.get("imap_server", "imap.hostinger.com")
                imap_port = account.get("imap_port", 993)
                mail = imaplib.IMAP4_SSL(imap_host, imap_port)
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


def _blacklist_lead(lead):
    """Best-effort: extract channel_id from the lead's YouTube URL and blacklist it."""
    try:
        from channel_blacklist import add_to_blacklist
        m = _YT_CHANNEL_RE.search(lead.get("youtube_url") or "")
        if m:
            add_to_blacklist(m.group(1), lead.get("channel_name") or "")
    except Exception:
        pass


def _run_instantly_sync():
    """
    Background: pull each lead's real state from the Instantly campaign and
    reconcile Notion + the dashboard.
      sent        -> Contacted (+ Email Sent From = Instantly)
      replied     -> Replied
      bounced     -> Bounced  (+ blacklist)
      unsubscribed-> Closed   (+ blacklist)
      queued      -> left as Queued
    Monotonic: never downgrades a terminal status (Replied/Closed/Bounced).
    """
    from instantly_helpers import instantly_ready, get_campaign_leads, classify_lead_status
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({
            "status": "running", "action": "instantly_sync",
            "progress": 0, "total": 0, "logs": [],
        })

    if not instantly_ready():
        _alog(f"[{_ts()}] ❌ Instantly not configured — add API key + Campaign ID in Settings")
        with _email_action_lock:
            _email_action_state["status"] = "error"
        return

    # ── 1) Pull all campaign leads from Instantly (paginated) ──────
    _alog(f"[{_ts()}]    Connecting to Instantly campaign…")
    inst_status = {}   # email(lower) -> bucket
    cursor, pages = None, 0
    while True:
        if _email_action_stop.is_set():
            _alog(f"[{_ts()}] ⏹ Stopped by user")
            with _email_action_lock: _email_action_state["status"] = "stopped"
            return
        items, cursor, err = get_campaign_leads(starting_after=cursor, limit=100)
        if err:
            _alog(f"[{_ts()}] ❌ Instantly API error: {err}")
            with _email_action_lock: _email_action_state["status"] = "error"
            return
        for it in items:
            em = str((it or {}).get("email") or "").strip().lower()
            if em:
                inst_status[em] = classify_lead_status(it)
        pages += 1
        _alog(f"[{_ts()}]    Pulled {len(inst_status)} Instantly lead(s)…")
        if not cursor or not items or pages > 200:
            break

    if not inst_status:
        _alog(f"[{_ts()}] ✅ No leads found in the Instantly campaign")
        with _email_action_lock:
            _email_action_state.update({"status": "completed", "progress": 100})
        return

    # ── 2) Reconcile against Notion (match by email) ───────────────
    _alog(f"[{_ts()}]    Matching {len(inst_status)} Instantly lead(s) against Notion…")
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
    except Exception as e:
        _alog(f"[{_ts()}] ❌ Notion fetch failed: {e}")
        with _email_action_lock: _email_action_state["status"] = "error"
        return

    TERMINAL = {"Replied", "Closed", "Bounced"}
    c = {"sent": 0, "replied": 0, "bounced": 0, "unsubscribed": 0, "queued": 0, "skipped": 0}
    leads = [_extract_full_lead(r) for r in records]
    total = len(leads)
    with _email_action_lock: _email_action_state["total"] = total

    for idx, lead in enumerate(leads, 1):
        if _email_action_stop.is_set():
            _alog(f"[{_ts()}] ⏹ Stopped by user")
            with _email_action_lock: _email_action_state["status"] = "stopped"
            return
        with _email_action_lock:
            _email_action_state["progress"] = int(idx / total * 100) if total else 100

        email  = str(lead.get("email") or "").strip().lower()
        bucket = inst_status.get(email)
        if not bucket:
            continue   # this lead isn't in the Instantly campaign
        cur   = lead.get("status") or "New"
        pid   = lead.get("id")
        cname = lead.get("channel_name") or email

        if cur in TERMINAL:      # monotonic — never revert a terminal status
            c["skipped"] += 1
            continue

        try:
            if bucket == "replied":
                if cur != "Replied":
                    notion.mark_replied(email)
                    c["replied"] += 1
                    _alog(f"[{_ts()}] 💬 Replied: {cname}")
            elif bucket == "bounced":
                notion.update_lead_status(pid, "Bounced")
                _blacklist_lead(lead); c["bounced"] += 1
                _alog(f"[{_ts()}] ⚠  Bounced: {cname}")
            elif bucket == "unsubscribed":
                notion.update_lead_status(pid, "Closed")
                _blacklist_lead(lead); c["unsubscribed"] += 1
                _alog(f"[{_ts()}] 🚫 Unsubscribed: {cname}")
            elif bucket == "sent":
                if cur != "Contacted":
                    notion.update_lead_status(pid, "Contacted")
                    try: notion.update_email_sent_from(pid, "Instantly")
                    except Exception: pass
                    c["sent"] += 1
                    _alog(f"[{_ts()}] ✅ Sent → Contacted: {cname}")
            else:
                c["queued"] += 1
        except Exception as ue:
            _alog(f"[{_ts()}] ⚠  Update failed for {cname}: {str(ue)[:120]}")

    _alog(f"[{_ts()}] 🏁 Instantly sync done — sent→contacted {c['sent']}, replied {c['replied']}, "
          f"bounced {c['bounced']}, unsub {c['unsubscribed']}, still-queued {c['queued']}")
    with _email_action_lock:
        _email_action_state.update({"status": "completed", "progress": 100})


def _run_qualify_preview():
    """
    Re-qualify every 'New' lead with the system's own intelligence
    (smart_scorer.intelligent_score_channel → entertainment/no-CTA/inactive get
    cut). PREVIEW ONLY: nothing is archived. Stores the flagged page IDs so the
    'Apply Cleanup' step can archive exactly what you reviewed.
    Fetch failures are KEPT (never auto-cut on missing data).
    """
    from smart_scorer import intelligent_score_channel
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({"status": "running", "action": "qualify_preview",
                                    "progress": 0, "total": 0, "logs": []})
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
    except Exception as e:
        _alog(f"[{_ts()}] ❌ Notion fetch failed: {e}")
        with _email_action_lock: _email_action_state["status"] = "error"
        return

    new_leads = [l for l in (_extract_full_lead(r) for r in records) if l.get("status") == "New"]
    total = len(new_leads)
    with _email_action_lock: _email_action_state["total"] = total
    _alog(f"[{_ts()}] ▷ Qualifying {total} New lead(s) — PREVIEW only, nothing removed yet")

    keep, cut_ids, cut_preview = 0, [], []
    for i, lead in enumerate(new_leads, 1):
        if _email_action_stop.is_set():
            _alog(f"[{_ts()}] ⏹ Stopped by user")
            with _email_action_lock: _email_action_state["status"] = "stopped"
            return
        with _email_action_lock:
            _email_action_state["progress"] = int(i / total * 100) if total else 100
        cname = lead.get("channel_name") or lead.get("email") or "?"

        try:
            cdata, videos = _fetch_youtube_for_lead(lead.get("youtube_url") or "")
        except Exception:
            cdata, videos = {}, []

        if not cdata:   # couldn't verify → keep to be safe (never cut on missing data)
            keep += 1
            _alog(f"[{_ts()}] [{i}/{total}] ⚠ {cname} — couldn't fetch YouTube, KEPT (unverified)")
            continue

        cdata["email"] = lead.get("email") or ""
        if videos:
            cdata["last_video_date"] = videos[0].get("published_at", "")
        if not cdata.get("subscriber_count"):
            cdata["subscriber_count"] = lead.get("subscriber_count") or 0

        result    = intelligent_score_channel(cdata, videos, days_since_last_video(videos))
        score     = result.get("score", 0)
        qualified = result.get("qualified", False)
        reason    = (result.get("reason") or "").replace("✅", "").replace("❌", "").strip()

        if qualified:
            keep += 1
            _alog(f"[{_ts()}] [{i}/{total}] ✅ KEEP  {cname}  (score {score}/10)")
        else:
            cut_ids.append(lead["id"])
            cut_preview.append({"name": cname, "score": score, "reason": reason})
            _alog(f"[{_ts()}] [{i}/{total}] ✂ CUT   {cname}  (score {score}/10) — {reason}")

    with _qualify_lock:
        _qualify_state.update({"cut_ids": cut_ids, "cut_preview": cut_preview,
                               "summary": {"total": total, "keep": keep, "cut": len(cut_ids)},
                               "preview_at": _ts()})
    _alog(f"[{_ts()}] 🏁 Preview complete — {keep} qualified, {len(cut_ids)} to cut.")
    if cut_ids:
        _alog(f"[{_ts()}] 👉 Review the CUT list above, then click 'Apply Cleanup' to archive "
              f"the {len(cut_ids)} flagged lead(s). (Recoverable from Notion Trash.)")
    with _email_action_lock:
        _email_action_state.update({"status": "completed", "progress": 100})


def _run_qualify_apply():
    """Archive the leads flagged by the most recent preview (recoverable)."""
    _email_action_stop.clear()
    with _email_action_lock:
        _email_action_state.update({"status": "running", "action": "qualify_apply",
                                    "progress": 0, "total": 0, "logs": []})
    with _qualify_lock:
        cut_ids = list(_qualify_state.get("cut_ids") or [])
    if not cut_ids:
        _alog(f"[{_ts()}] ⚠ Nothing to apply — run 'Qualify Leads (Preview)' first.")
        with _email_action_lock: _email_action_state["status"] = "completed"
        return

    notion = NotionManager()
    total, done = len(cut_ids), 0
    with _email_action_lock: _email_action_state["total"] = total
    _alog(f"[{_ts()}] ▷ Archiving {total} flagged lead(s) — recoverable from Notion Trash")
    for i, pid in enumerate(cut_ids, 1):
        if _email_action_stop.is_set():
            _alog(f"[{_ts()}] ⏹ Stopped ({done}/{total} archived)")
            with _email_action_lock: _email_action_state["status"] = "stopped"
            return
        try:
            notion.archive_lead(pid); done += 1
        except Exception as e:
            _alog(f"[{_ts()}] ⚠ Archive failed for {pid}: {str(e)[:80]}")
        with _email_action_lock:
            _email_action_state["progress"] = int(i / total * 100)

    with _qualify_lock:   # consume the list so it can't be applied twice
        _qualify_state.update({"cut_ids": [], "cut_preview": [], "summary": {}, "preview_at": None})
    _alog(f"[{_ts()}] 🏁 Cleanup done — {done}/{total} leads archived (now in Notion Trash).")
    with _email_action_lock:
        _email_action_state.update({"status": "completed", "progress": 100})


# ── Email action API endpoints ─────────────────────────────────

def _start_action(target_fn, name: str):
    """Helper: reject if busy, else start background thread."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    with _email_action_lock:
        if _email_action_state.get("status") == "running":
            action = _email_action_state.get("action", "?")
            return jsonify({"error": f"Action already running: {action}"}), 400
    _email_action_stop.clear()   # ensure stop flag is clear before new thread starts
    t = threading.Thread(target=target_fn, daemon=True, name=f"fuelvia-{name}")
    t.start()
    return jsonify({"success": True})


def _get_limit_from_request():
    """Read an optional 'limit' (how many to send) from the POST body."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        lim = data.get("limit")
        if lim in (None, "", "all"):
            return None
        lim = int(lim)
        return lim if lim > 0 else None
    except Exception:
        return None


@app.route("/api/send-emails", methods=["POST"])
def api_send_emails():
    limit = _get_limit_from_request()
    return _start_action(lambda: _run_send_emails(limit=limit), "send-emails")


@app.route("/api/send-followup", methods=["POST"])
def api_send_followup():
    limit = _get_limit_from_request()
    return _start_action(lambda: _run_send_followup(limit=limit), "send-followup")


@app.route("/api/check-replies", methods=["POST"])
def api_check_replies():
    return _start_action(_run_check_replies, "check-replies")


@app.route("/api/instantly-sync", methods=["POST"])
def api_instantly_sync():
    return _start_action(_run_instantly_sync, "instantly-sync")


@app.route("/api/qualify-preview", methods=["POST"])
def api_qualify_preview():
    return _start_action(_run_qualify_preview, "qualify-preview")


@app.route("/api/qualify-apply", methods=["POST"])
def api_qualify_apply():
    return _start_action(_run_qualify_apply, "qualify-apply")


@app.route("/api/qualify-status")
def api_qualify_status():
    """How many leads the last preview flagged for cutting (for the Apply confirm)."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    with _qualify_lock:
        return jsonify({
            "cut_count":  len(_qualify_state.get("cut_ids") or []),
            "summary":    _qualify_state.get("summary") or {},
            "preview_at": _qualify_state.get("preview_at"),
        })


@app.route("/api/campaign-counts")
def api_campaign_counts():
    """Pending counts for the campaign setup screen:
    cold_pending = New leads, followup_pending = Contacted leads."""
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        counts  = {}
        for r in records:
            s = (((r.get("properties") or {}).get("Status") or {}).get("select") or {}).get("name") or "New"
            counts[s] = counts.get(s, 0) + 1
        return jsonify({
            "success": True,
            "cold_pending":     counts.get("New", 0),
            "followup_pending": counts.get("Contacted", 0),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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


# ── Keep-alive ping (prevents Render free-tier sleep) ─────────

@app.route("/api/ping")
def api_ping():
    """Browser pings this every 5 minutes to keep Render awake during campaigns."""
    return jsonify({"ok": True, "ts": _ts()})


# ── CRM Activity History ───────────────────────────────────────

@app.route("/api/activity-crm")
def api_activity_crm():
    """
    Returns compact CRM history for all 3 campaign actions.
    Pulls from Notion — persists across server restarts and deploys.
    """
    if not _auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        notion  = NotionManager()
        records = notion.get_all_leads()
        leads   = [_extract_full_lead(r) for r in records]

        sent_emails, followups, replies = [], [], []

        for l in leads:
            status = l.get("status", "New")

            # ── Cold emails sent ──
            if status not in ("New", ""):
                sent_emails.append({
                    "channel":   l.get("channel_name") or "—",
                    "to_email":  l.get("email") or "—",
                    "from_acct": l.get("email_sent_from") or "—",
                    "date":      (l.get("last_contact") or l.get("date_added") or "").split("T")[0],
                    "preview":   (l.get("day1_email_body") or "")[:120].strip(),
                    "status":    status,
                    "yt_url":    l.get("youtube_url") or "",
                })

            # ── Follow-ups sent ──
            if l.get("day2_sent"):
                followups.append({
                    "channel":   l.get("channel_name") or "—",
                    "to_email":  l.get("email") or "—",
                    "from_acct": l.get("email_sent_from") or "—",
                    "date":      (l.get("last_contact") or "").split("T")[0],
                    "status":    status,
                    "yt_url":    l.get("youtube_url") or "",
                })

            # ── Replies received ──
            if l.get("replied"):
                replies.append({
                    "channel":       l.get("channel_name") or "—",
                    "from_email":    l.get("email") or "—",
                    "reply_date":    (l.get("reply_date") or "").split("T")[0],
                    "reply_preview": (l.get("reply_message") or "")[:150].strip(),
                    "yt_url":        l.get("youtube_url") or "",
                })

        # Most recent first
        sent_emails.sort(key=lambda x: x["date"], reverse=True)
        followups.sort(key=lambda x: x["date"], reverse=True)
        replies.sort(key=lambda x: x["reply_date"], reverse=True)

        return jsonify({
            "sent_emails": sent_emails[:50],
            "followups":   followups[:50],
            "replies":     replies[:50],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


# ── ERROR HANDLERS (no stack trace leaks) ──────────────────────

@app.errorhandler(404)
def handle_404(e):
    """Serve decoy page on 404."""
    from security import _get_decoy_page
    return _get_decoy_page(), 200

@app.errorhandler(500)
def handle_500(e):
    """Log error internally, return generic response."""
    import traceback
    print(f"[ERROR 500] {traceback.format_exc()}")
    return jsonify({"error": "Something went wrong"}), 500

@app.errorhandler(403)
def handle_403(e):
    """Forbidden — serve decoy."""
    from security import _get_decoy_page
    return _get_decoy_page(), 200


# ── Entry point ────────────────────────────────────────────────

def _startup_checks():
    """Run at boot — log config health and warm up critical systems."""
    import os as _os
    # Read LIVE from settings store (UI overrides + env) so boot log matches reality
    _YT_KEYS    = settings_store.get_list("YOUTUBE_API_KEYS")
    _NOTION_KEY = settings_store.get("NOTION_API_KEY")
    _NOTION_DB  = settings_store.get("NOTION_DATABASE_ID")
    _CLAUDE_KEY = settings_store.get("CLAUDE_API_KEY")
    print("=" * 56)
    print("  FUELVIA Lead Generation System — Starting Up")
    print("=" * 56)

    # YouTube API keys
    if _YT_KEYS:
        print(f"  [OK] YouTube API: {len(_YT_KEYS)} key(s) loaded")
    else:
        print("  [!!] YouTube API: NO KEYS — add them in Settings")

    # Notion
    if _NOTION_KEY and _NOTION_DB:
        print("  [OK] Notion: configured")
    else:
        print("  [!!] Notion: MISSING KEY or DATABASE_ID")

    # Claude
    if _CLAUDE_KEY:
        print("  [OK] Claude API: configured")
    else:
        print("  [WR] Claude API: not set — fallback email templates will be used")

    # Email accounts
    print(f"  [OK] Email accounts: {len(OUTREACH_ACCOUNTS)} loaded")
    for acc in OUTREACH_ACCOUNTS:
        print(f"       • {acc['email']}")

    # SQLite check
    try:
        from channel_blacklist import blacklist_size
        bl = blacklist_size()
        print(f"  [OK] Blacklist DB: {bl} channels")
    except Exception as e:
        print(f"  [WR] Blacklist DB: {e}")

    try:
        from daily_send_limit import reset_expired, get_today_count
        reset_expired()
        print("  [OK] Daily send limits: OK")
    except Exception as e:
        print(f"  [WR] Daily send limits: {e}")

    print("=" * 56)


# Alias for audit compatibility
def get_dashboard_data():
    """Get dashboard stats (audit-compatible function)"""
    notion  = NotionManager()
    records = notion.get_all_leads()
    counts  = {}
    for r in records:
        s = (((r.get("properties") or {}).get("Status") or {}).get("select") or {}).get("name") or "New"
        counts[s] = counts.get(s, 0) + 1
    return {
        "leads_total":      len(records),
        "emails_sent":      (counts.get("Contacted", 0) + counts.get("Follow-up 1", 0) +
                            counts.get("Follow-up Sent", 0) + counts.get("Follow-up 1 Sent", 0) +
                            counts.get("Replied", 0) + counts.get("Closed", 0)),
        "replies_received": counts.get("Replied", 0),
        "new_leads":        counts.get("New", 0),
        "queued":           counts.get("Queued", 0),
        "contacted":        counts.get("Contacted", 0),
        "closed":           counts.get("Closed", 0),
        "bounced":          counts.get("Bounced", 0),
    }


if __name__ == "__main__":
    import os as _os
    _port = int(_os.environ.get("PORT", 5000))  # Render sets $PORT; local defaults to 5000
    _startup_checks()
    print(f"  Open:     http://127.0.0.1:{_port}")
    print(f"  Password: fuelvia2025")
    print("=" * 56 + "\n")
    app.run(debug=False, threaded=True, host="0.0.0.0", port=_port)
