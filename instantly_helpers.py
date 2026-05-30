# ============================================================
# INSTANTLY HELPERS — Instantly.ai API integration
# ============================================================
# Alternative send mode: instead of sending email directly via
# SMTP, push the lead (with the Claude-written personalization)
# into an Instantly campaign. Instantly then handles the actual
# sending + follow-up sequences on its own infrastructure.
#
# Toggled via the SEND_MODE setting ("smtp" | "instantly").
# Keys (INSTANTLY_API_KEY, INSTANTLY_CAMPAIGN_ID) are read LIVE
# from the settings store (UI-editable, .env fallback).
# ============================================================

import json
import requests
import settings_store

INSTANTLY_API_URL = "https://api.instantly.ai/api/v2/leads"


def instantly_ready() -> bool:
    """True if both API key and campaign ID are configured."""
    return bool(settings_store.get("INSTANTLY_API_KEY")) and \
           bool(settings_store.get("INSTANTLY_CAMPAIGN_ID"))


_GENERIC_LOCALPARTS = {
    "info", "hello", "hi", "hey", "contact", "team", "admin", "mail", "email",
    "support", "business", "official", "media", "studio", "yt", "youtube",
    "sales", "help", "noreply", "no", "reply", "the", "hq", "agency", "co",
    "social", "marketing", "booking", "bookings", "inquiries", "enquiries",
}
_NON_NAME_WORDS = {
    "the", "tech", "official", "real", "daily", "my", "team", "studio", "media",
    "channel", "tv", "news", "review", "reviews", "mr", "mrs", "ms", "dr", "prof",
    "digital", "creative", "online", "best", "top", "pro", "global",
}


def _first_name(name: str, email: str = "") -> str:
    """
    Best-effort HUMAN first name for Instantly's {{firstName}}.
      1) channel/display name — only if it looks like a person (≤2 words, not a brand word)
      2) email local-part.
    Returns '' if no confident human name (so the sequence can fall back cleanly).
    """
    base = name or ""
    for sep in ["-", "|", "–", "—", ":", "(", "/", ",", "@"]:
        if sep in base:
            base = base.split(sep)[0]
    toks = base.strip().split()
    if (toks and len(toks) <= 2 and toks[0].isalpha()
            and 2 <= len(toks[0]) <= 15 and toks[0].lower() not in _NON_NAME_WORDS):
        return toks[0].capitalize()

    if email and "@" in email:
        local = email.split("@")[0]
        for ch in "._-0123456789+":
            local = local.replace(ch, " ")
        for part in local.split():
            if part.isalpha() and 2 <= len(part) <= 15 and part.lower() not in _GENERIC_LOCALPARTS:
                return part.capitalize()
    return ""


def add_lead_to_instantly(email: str,
                          channel_name: str,
                          youtube_url: str,
                          email_body: str,
                          subject: str = "",
                          subscriber_count=0,
                          niche: str = "") -> tuple:
    """
    Push one lead into the configured Instantly campaign.

    Returns (success: bool, error_msg: str).

    Maps Fuelvia lead data → Instantly lead fields:
      email             -> email
      first name        -> first_name   ({{firstName}})
      channel_name      -> company_name
      youtube_url       -> website
      Claude email body -> personalization  ({{personalization}})
      campaign id       -> campaign
      + custom_variables you can use as {{...}} in the sequence:
        email_subject, email_body, channel_name, subscriber_count, niche, youtube_url
    """
    api_key     = settings_store.get("INSTANTLY_API_KEY")
    campaign_id = settings_store.get("INSTANTLY_CAMPAIGN_ID")

    if not api_key:
        return False, "INSTANTLY_API_KEY not set (configure in Settings)"
    if not campaign_id:
        return False, "INSTANTLY_CAMPAIGN_ID not set (configure in Settings)"
    if not email:
        return False, "No email address for lead"

    payload = {
        "email":           email,
        "first_name":      _first_name(channel_name, email),
        "company_name":    channel_name,
        "website":         youtube_url,
        "personalization": email_body,
        "campaign":        campaign_id,
        "custom_variables": {
            "email_subject":    subject,      # use as {{email_subject}} in the sequence subject line
            "email_body":       email_body,   # use as {{email_body}} (same as {{personalization}})
            "channel_name":     channel_name,
            "subscriber_count": subscriber_count,
            "niche":            niche,
            "youtube_url":      youtube_url,
        },
    }

    try:
        resp = requests.post(
            INSTANTLY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return True, ""
        # Surface the API's error message for easier debugging
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:200]
        return False, f"HTTP {resp.status_code}: {detail}"
    except Exception as e:
        return False, str(e)


def test_instantly() -> tuple:
    """
    Lightweight connectivity/credentials check for the Settings 'Test' button.
    Lists campaigns (read-only) to verify the API key works.
    Returns (success: bool, message: str).
    """
    api_key = settings_store.get("INSTANTLY_API_KEY")
    if not api_key:
        return False, "INSTANTLY_API_KEY not set"
    try:
        resp = requests.get(
            "https://api.instantly.ai/api/v2/campaigns",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        if resp.status_code == 200:
            cid = settings_store.get("INSTANTLY_CAMPAIGN_ID")
            return True, f"Instantly OK — API key valid. Campaign ID {'set' if cid else 'MISSING'}."
        return False, f"HTTP {resp.status_code}: {resp.text[:150]}"
    except Exception as e:
        return False, str(e)


# ── Polling / status reconcile (for the "Sync from Instantly" button) ──────

def _headers():
    return {
        "Authorization": f"Bearer {settings_store.get('INSTANTLY_API_KEY')}",
        "Content-Type":  "application/json",
    }


def get_campaign_leads(starting_after=None, limit: int = 100) -> tuple:
    """
    Fetch one page of leads for the configured campaign.
    Returns (items: list[dict], next_cursor: str|None, error: str|None).

    Instantly v2 list endpoint: POST /api/v2/leads/list
      body: {"campaign": <id>, "limit": N, "starting_after": <cursor>}
      resp: {"items": [...], "next_starting_after": <cursor>}
    Written defensively — tolerates either {"items": [...]} or a bare list,
    and several cursor field names.
    """
    api_key     = settings_store.get("INSTANTLY_API_KEY")
    campaign_id = settings_store.get("INSTANTLY_CAMPAIGN_ID")
    if not api_key:
        return [], None, "INSTANTLY_API_KEY not set"
    if not campaign_id:
        return [], None, "INSTANTLY_CAMPAIGN_ID not set"

    body = {"campaign": campaign_id, "limit": limit}
    if starting_after:
        body["starting_after"] = starting_after

    try:
        resp = requests.post(
            "https://api.instantly.ai/api/v2/leads/list",
            headers=_headers(), json=body, timeout=30,
        )
        if resp.status_code != 200:
            return [], None, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        if isinstance(data, list):
            return data, None, None
        items = data.get("items") or data.get("data") or data.get("leads") or []
        cursor = (data.get("next_starting_after") or data.get("next_cursor")
                  or data.get("starting_after"))
        return items, cursor, None
    except Exception as e:
        return [], None, str(e)


def _truthy(v) -> bool:
    return v not in (None, "", 0, "0", False, "false", "False")


def classify_lead_status(lead: dict) -> str:
    """
    Map a raw Instantly v2 lead object to one of:
      'replied' | 'bounced' | 'unsubscribed' | 'sent' | 'queued'

    Grounded in the REAL v2 lead shape (confirmed via a live test lead):
      status (int), email_reply_count, email_open_count, email_click_count,
      status_summary (dict, e.g. {} when no activity), verification_status.
    Priority (most decisive first): replied > bounced > unsubscribed > sent > queued.

    NOTE: the v2 lead-list object has no plain "email_sent_count". Until a lead
    has activity, opens/clicks/replies are the reliable "it was sent" signals,
    plus whatever status_summary fills in. When the campaign first sends for real
    we should confirm the exact 'sent' marker (status_summary key or status int)
    and, if needed, switch to the /api/v2/emails endpoint for definitive sends.
    """
    if not isinstance(lead, dict):
        return "queued"
    g = lead.get

    # status_summary is a DICT in v2 — flatten to a searchable blob
    summary = g("status_summary")
    summary = summary if isinstance(summary, dict) else {}
    blob  = json.dumps(summary).lower()
    label = str(g("lead_status") or "").lower()

    reply_count = g("email_reply_count") or g("reply_count") or 0
    open_count  = g("email_open_count")  or 0
    click_count = g("email_click_count") or 0

    # ── Replied (human reply — most valuable) ──
    if _truthy(reply_count) or _truthy(g("is_replied")) \
       or "repl" in blob or "interested" in blob or "interested" in label:
        return "replied"

    # ── Bounced ──
    verif = str(g("verification_status") or "").lower()
    if _truthy(g("is_bounced")) or "bounc" in blob or "bounc" in label \
       or "bounc" in verif or verif == "invalid":
        return "bounced"

    # ── Unsubscribed ──
    if _truthy(g("is_unsubscribed")) or "unsub" in blob or "unsub" in label:
        return "unsubscribed"

    # ── Sent (no plain sent_count in v2; use activity + summary as proxy) ──
    sent_count = g("email_sent_count") or g("emails_sent") or 0
    if _truthy(sent_count) or _truthy(open_count) or _truthy(click_count) \
       or "sent" in blob or "contacted" in blob:
        return "sent"

    return "queued"


def get_campaign_analytics() -> tuple:
    """
    Optional aggregate stats for the configured campaign.
    Returns (data: dict|None, error: str|None).
    GET /api/v2/campaigns/analytics?id=<campaign_id>
    """
    api_key     = settings_store.get("INSTANTLY_API_KEY")
    campaign_id = settings_store.get("INSTANTLY_CAMPAIGN_ID")
    if not api_key or not campaign_id:
        return None, "Instantly not configured"
    try:
        resp = requests.get(
            "https://api.instantly.ai/api/v2/campaigns/analytics",
            headers=_headers(), params={"id": campaign_id}, timeout=25,
        )
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:150]}"
        return resp.json(), None
    except Exception as e:
        return None, str(e)
