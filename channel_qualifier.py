# ============================================================
# CHANNEL QUALIFIER - Pure Python, Zero Claude
# ============================================================
# Qualifies leads based on hard facts only:
#   REQUIRED: email found (description or video descriptions)
#   REQUIRED: last post within 90 days
#   SOFT:     subscriber count (already pre-filtered in search)
#   SOFT:     location (if email exists → qualify regardless)
#   SOFT:     niche (already matched in YouTube search query)
#
# Score is for SORTING only — does NOT disqualify anyone.
# If email + active → QUALIFIED. That's it.
# ============================================================

import re
from typing import Dict, List, Optional, Tuple

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

EXCLUDED_DOMAINS = {
    "example.com", "youremail.com", "gmail.com", "email.com",
    "noreply.com", "sentry.io", "wixpress.com", "domain.com",
    "yourname.com", "company.com", "business.com"
}


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract first valid business email from any text block."""
    if not text:
        return None
    for match in EMAIL_REGEX.findall(text):
        domain = match.split("@")[1].lower()
        if domain not in EXCLUDED_DOMAINS and "." in domain:
            return match.lower()
    return None


def extract_email_from_all_sources(
    channel_desc: str,
    videos_data: List[Dict]
) -> Optional[str]:
    """
    Try to find a business email in order of priority:
      1. Channel description
      2. Video descriptions (last 5, newest first)

    Returns the first valid email found, or None.
    """
    # 1. Channel description
    email = extract_email_from_text(channel_desc)
    if email:
        return email

    # 2. Each video description
    for video in videos_data:
        email = extract_email_from_text(video.get("description", ""))
        if email:
            return email

    return None


def _activity_score(days_since_video: int) -> Tuple[int, str]:
    """Score recency of last post (0–4). Used for sorting only."""
    if days_since_video <= 7:
        return 4, f"Posted {days_since_video}d ago (very active)"
    if days_since_video <= 30:
        return 3, f"Posted {days_since_video}d ago (active)"
    if days_since_video <= 60:
        return 2, f"Posted {days_since_video}d ago (recent)"
    if days_since_video <= 90:
        return 1, f"Posted {days_since_video}d ago (borderline)"
    return 0, f"Posted {days_since_video}d ago (inactive)"


def _subscriber_score(subs: int) -> Tuple[int, str]:
    """Score subscriber count (0–3). Already in range from search filter."""
    if subs >= 20_000:
        return 3, f"{subs:,} subscribers (large)"
    if subs >= 10_000:
        return 2, f"{subs:,} subscribers (solid)"
    if subs >= 1_000:
        return 1, f"{subs:,} subscribers (small)"
    return 0, f"{subs:,} subscribers (very small)"


def qualify_channel(
    channel_data: Dict,
    videos_data: List[Dict],
    days_since_video: int,
) -> Dict:
    """
    Qualify a YouTube channel as a lead.

    HARD #1  Email found in channel desc OR any video desc  → no email = REJECT
    HARD #2  Last post within 90 days                       → inactive = REJECT
    SOFT     Subscriber count + recency affect score only (0-7)
    """
    channel_name = channel_data.get("channel_name", "?")
    channel_desc = channel_data.get("description", "")

    # ── HARD FILTER 1: find email ─────────────────────────────
    email = extract_email_from_all_sources(channel_desc, videos_data)
    if not email:
        return {
            "qualified": False,
            "email": None,
            "score": 0,
            "reason": "No email found in description or videos",
            "email_source": None,
        }

    email_source = "channel_desc" if extract_email_from_text(channel_desc) else "video_desc"

    # ── HARD FILTER 2: activity ───────────────────────────────
    if days_since_video > 90:
        return {
            "qualified": False,
            "email": email,
            "score": 0,
            "reason": f"Inactive: last video {days_since_video} days ago (limit: 90)",
            "email_source": email_source,
        }

    # ── SOFT SCORING ──────────────────────────────────────────
    act_pts, act_note = _activity_score(days_since_video)
    sub_pts, sub_note = _subscriber_score(channel_data.get("subscriber_count", 0))
    total_score = act_pts + sub_pts   # max 7

    return {
        "qualified":    True,
        "email":        email,
        "score":        total_score,
        "reason":       f"{act_note} | {sub_note} | email from {email_source}",
        "email_source": email_source,
    }
