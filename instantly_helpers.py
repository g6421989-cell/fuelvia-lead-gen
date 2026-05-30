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

import requests
import settings_store

INSTANTLY_API_URL = "https://api.instantly.ai/api/v2/leads"


def instantly_ready() -> bool:
    """True if both API key and campaign ID are configured."""
    return bool(settings_store.get("INSTANTLY_API_KEY")) and \
           bool(settings_store.get("INSTANTLY_CAMPAIGN_ID"))


def add_lead_to_instantly(email: str,
                          channel_name: str,
                          youtube_url: str,
                          email_body: str,
                          subscriber_count=0,
                          niche: str = "") -> tuple:
    """
    Push one lead into the configured Instantly campaign.

    Returns (success: bool, error_msg: str).

    Maps Fuelvia lead data → Instantly lead fields:
      email            -> email
      channel_name     -> first_name, company_name
      youtube_url      -> website
      Claude email body-> personalization
      campaign id      -> campaign
      + custom_variables: channel_name, subscriber_count, niche, youtube_url
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
        "first_name":      channel_name,
        "company_name":    channel_name,
        "website":         youtube_url,
        "personalization": email_body,
        "campaign":        campaign_id,
        "custom_variables": {
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
    Map a raw Instantly lead object to one of:
      'replied' | 'bounced' | 'unsubscribed' | 'sent' | 'queued'

    Defensive: Instantly's exact field names/enums vary, so we check several
    likely keys. Priority (most decisive first): replied > bounced >
    unsubscribed > sent > queued. Adjust here once a real lead payload is seen.
    """
    if not isinstance(lead, dict):
        return "queued"

    g = lead.get  # shorthand

    # ── Replied (a human reply — most valuable) ──
    reply_count = g("email_reply_count") or g("reply_count") or g("replies") or 0
    if _truthy(reply_count) or _truthy(g("is_replied")) or _truthy(g("replied")):
        return "replied"
    # lead_status / status enums that some accounts use for "replied"
    status_label = str(g("status_summary") or g("lead_status") or "").lower()
    if "repl" in status_label or "interested" in status_label:
        return "replied"

    # ── Bounced ──
    if _truthy(g("is_bounced")) or _truthy(g("bounced")) or "bounc" in status_label:
        return "bounced"
    verif = str(g("verification_status") or "").lower()
    if "bounc" in verif or verif in ("invalid", "risky"):
        return "bounced"

    # ── Unsubscribed ──
    if _truthy(g("is_unsubscribed")) or _truthy(g("unsubscribed")) or "unsub" in status_label:
        return "unsubscribed"

    # ── Sent (at least one email went out) ──
    sent_count = (g("email_sent_count") or g("emails_sent_count")
                  or g("sent_count") or g("emails_sent") or 0)
    if _truthy(sent_count) or "contact" in status_label or "active" in status_label:
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
