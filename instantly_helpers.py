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
