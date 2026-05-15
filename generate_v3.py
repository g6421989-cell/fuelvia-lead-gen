"""
FUELVIA LEAD GENERATION v3 — CLEAN ARCHITECTURE
================================================
What changed from v2
  - Email extracted by CODE from channel desc + last 5 video descs
  - Qualification by CODE only (email exists + active ≤90 days)
  - No subjective filters (no "professional", "hobby", "established")
  - Location is SOFT: if email found → qualify regardless
  - Claude used ONLY to write personalized emails (never to score)
  - Claude receives FULL channel data + recent video titles

Qualification logic (simple)
  REQUIRED  email found anywhere (description or any video description)
  REQUIRED  last video posted within 90 days
  SOFT      subscriber count (pre-filtered in search)
  SOFT      location (email overrides any mismatch)
  SOFT      niche (already matched by search keyword)

USAGE: python generate_v3.py
"""

import re
import time
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build

from config import (
    YOUTUBE_APIS, NICHE_SEARCH_TERMS, NICHE_OPTIONS, LOCATION_OPTIONS,
    SUBSCRIBER_RANGES, EMAIL_ROTATION_DELAY, SENDER_NAME, COMPANY_NAME,
)
from notion_manager import NotionManager
from email_helpers import EmailRotator, send_report_email
from claude_helpers import write_personalized_initial_email
from youtube_enricher import get_videos_for_channel, get_days_since_last_video
from channel_qualifier import qualify_channel


# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────

def print_banner():
    print("\n" + "=" * 70)
    print("   FUELVIA LEAD GENERATION v3")
    print("   Code qualifies  |  Claude personalizes")
    print("=" * 70 + "\n")


def select_option(prompt, options):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            choice = int(input(f"\nSelect (1-{len(options)}): "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except (ValueError, KeyboardInterrupt):
            pass
        print(f"  Enter a number 1–{len(options)}")


def get_user_inputs():
    print_banner()

    niche_key = select_option("NICHE:", NICHE_OPTIONS)
    if niche_key == "Custom":
        raw = input("  Enter keywords (comma-separated): ").strip()
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
    else:
        keywords = NICHE_SEARCH_TERMS.get(niche_key, [niche_key])

    location_key = select_option("LOCATION:", list(LOCATION_OPTIONS.keys()))
    location_list = LOCATION_OPTIONS[location_key]

    sub_range_key = select_option("SUBSCRIBER RANGE:", list(SUBSCRIBER_RANGES.keys()))
    sub_range = SUBSCRIBER_RANGES[sub_range_key]

    while True:
        try:
            raw_count = input("\nHow many leads? (default 50): ").strip()
            max_leads = int(raw_count) if raw_count else 50
            break
        except ValueError:
            print("  Enter a valid number.")

    return niche_key, keywords, location_list, sub_range, max_leads


# ─────────────────────────────────────────────────────────────
# YOUTUBE HELPERS
# ─────────────────────────────────────────────────────────────

def get_youtube_client(api_index: int):
    key = YOUTUBE_APIS[api_index % len(YOUTUBE_APIS)]
    return build("youtube", "v3", developerKey=key), api_index


_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
_EXCLUDED  = {"example.com", "youremail.com", "gmail.com", "email.com",
              "noreply.com", "sentry.io", "wixpress.com"}

def _extract_email(text: str):
    for m in _EMAIL_RE.findall(text or ""):
        if m.split("@")[1].lower() not in _EXCLUDED:
            return m.lower()
    return None


def get_channel_details(youtube, channel_id: str):
    """Fetch basic channel info (name, subs, description)."""
    try:
        resp = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id,
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        item  = items[0]
        desc  = item["snippet"].get("description", "")
        subs  = int(item["statistics"].get("subscriberCount", 0))
        return {
            "channel_name":    item["snippet"]["title"],
            "subscriber_count": subs,
            "description":     desc,          # keep full description
            "youtube_url":     f"https://youtube.com/channel/{channel_id}",
            "channel_id":      channel_id,
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# SCRAPE
# ─────────────────────────────────────────────────────────────

def scrape_youtube(keywords, location_list, sub_range, max_leads):
    """Multi-keyword × multi-location search. Returns raw channel list."""
    api_index = 0
    youtube, api_index = get_youtube_client(api_index)

    sub_min, sub_max = sub_range
    seen_ids  = set()
    raw       = []
    search_no = 0

    print(f"\nSearching {len(keywords)} keywords × {len(location_list)} location(s)...\n")

    for keyword in keywords:
        for loc in location_list:
            search_no += 1
            query = f"{keyword} {loc}".strip() if loc else keyword
            print(f"  [{search_no:02d}] '{query}'")

            next_page = None
            pages = 0

            while pages < 3:                        # up to 150 results per combo
                try:
                    params = {
                        "part": "snippet",
                        "q": query,
                        "type": "channel",
                        "maxResults": 50,
                        "relevanceLanguage": "en",
                    }
                    if next_page:
                        params["pageToken"] = next_page

                    resp  = youtube.search().list(**params).execute()
                    items = resp.get("items", [])
                    if not items:
                        break

                    for item in items:
                        cid = item["snippet"]["channelId"]
                        if cid in seen_ids:
                            continue

                        details = get_channel_details(youtube, cid)
                        if not details:
                            continue

                        subs = details["subscriber_count"]
                        if subs < sub_min or (sub_max and subs > sub_max):
                            continue

                        details["niche"]    = keyword
                        details["location"] = loc or "Global"
                        raw.append(details)
                        seen_ids.add(cid)

                    next_page = resp.get("nextPageToken")
                    if not next_page:
                        break
                    pages += 1
                    time.sleep(0.4)

                except Exception as e:
                    if "quotaExceeded" in str(e) or "403" in str(e):
                        print(f"       quota hit — rotating API key")
                        api_index = (api_index + 1) % len(YOUTUBE_APIS)
                        youtube, api_index = get_youtube_client(api_index)
                    else:
                        print(f"       error: {e}")
                    break

            print(f"       total so far: {len(raw)}")
            time.sleep(0.3)

    print(f"\n  Found {len(raw)} unique channels in subscriber range\n")
    return raw, youtube, api_index


# ─────────────────────────────────────────────────────────────
# ENRICH + QUALIFY
# ─────────────────────────────────────────────────────────────

def enrich_and_qualify(raw_channels, youtube, max_leads):
    """
    For each channel:
      1. Fetch last 5 video descriptions (YouTube API)
      2. Extract email from channel desc + video descs (code)
      3. Qualify: email exists AND last post ≤ 90 days (code)
      4. Score for sort priority (code)
    Returns sorted list of qualified channels.
    """
    print("Fetching video data + qualifying channels...\n")

    qualified = []
    stats = {"no_email": 0, "inactive": 0, "qualified": 0}

    for i, channel in enumerate(raw_channels):
        name = channel.get("channel_name", "?")
        cid  = channel.get("channel_id", "")

        print(f"  [{i+1:03d}/{len(raw_channels)}] {name}")

        # Fetch last 5 videos
        try:
            videos_data = get_videos_for_channel(youtube, cid, max_videos=5)
        except Exception:
            videos_data = []

        # Days since last post
        try:
            days_since = get_days_since_last_video(youtube, cid)
        except Exception:
            days_since = 999

        channel["days_since_last_video"] = days_since
        channel["videos_data"]           = videos_data

        # Qualify (pure Python)
        result = qualify_channel(channel, videos_data, days_since)

        if not result["qualified"]:
            reason = result["reason"]
            print(f"       SKIP — {reason}")
            if "No email" in reason:
                stats["no_email"] += 1
            else:
                stats["inactive"] += 1
            continue

        # Attach email and score back to channel dict
        channel["email"]      = result["email"]
        channel["score"]      = result["score"]
        channel["score_reason"] = result["reason"]

        qualified.append(channel)
        stats["qualified"] += 1

        email_src = result.get("email_source", "")
        src_tag   = "(from video desc)" if email_src == "video_desc" else ""
        print(f"       QUALIFIED — score {result['score']}/7 | {result['email']} {src_tag}")

        # Stop collecting once we have enough
        if len(qualified) >= max_leads:
            print(f"\n  Target of {max_leads} reached — stopping early.\n")
            break

        time.sleep(0.3)   # be gentle with the API

    # Sort best leads first (highest score = most recent + most subs)
    qualified.sort(key=lambda c: c["score"], reverse=True)

    print(f"\n  Qualification summary")
    print(f"    Checked   : {i + 1}")
    print(f"    No email  : {stats['no_email']}")
    print(f"    Inactive  : {stats['inactive']}")
    print(f"    Qualified : {stats['qualified']}")

    return qualified


# ─────────────────────────────────────────────────────────────
# EMAIL SENDING
# ─────────────────────────────────────────────────────────────

def send_email_smtp(account, to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"]    = f"{SENDER_NAME} - {COMPANY_NAME} <{account['email']}>"
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(account["smtp_server"], account["smtp_port"]) as srv:
        srv.starttls()
        srv.login(account["email"], account["password"])
        srv.sendmail(account["email"], to_email, msg.as_string())


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    niche_key, keywords, location_list, sub_range, max_leads = get_user_inputs()

    print("\n" + "=" * 70)
    print("  Starting lead generation…")
    print("=" * 70)

    # 1. Scrape YouTube
    raw_channels, youtube, used_api = scrape_youtube(
        keywords, location_list, sub_range, max_leads
    )

    if not raw_channels:
        print("\nNo channels found. Try a broader search.\n")
        return

    # 2. Enrich + qualify (no Claude)
    qualified = enrich_and_qualify(raw_channels, youtube, max_leads)

    if not qualified:
        print("\nNo qualified leads found. Try broader search terms.\n")
        return

    # 3. Send personalized emails
    notion   = NotionManager()
    rotator  = EmailRotator()
    sent     = 0
    skipped  = 0

    print(f"\nSending personalized emails ({len(qualified)} leads)…\n")

    for i, lead in enumerate(qualified):
        email = lead["email"]
        name  = lead["channel_name"]

        # Duplicate check
        is_dup, _ = notion.check_duplicate(email)
        if is_dup:
            print(f"  [{i+1}] SKIP duplicate — {name}")
            skipped += 1
            continue

        # Claude writes the email (full context)
        print(f"  [{i+1}] Writing email for {name}…")
        subject, body = write_personalized_initial_email(
            lead,                           # full channel dict
            lead.get("videos_data", []),    # last 5 videos
        )

        # Send
        account = rotator.get_next_account()
        try:
            send_email_smtp(account, email, subject, body)

            # Save to Notion
            notion.create_lead({
                "channel_name":    name,
                "email":           email,
                "youtube_url":     lead.get("youtube_url", ""),
                "subscriber_count": lead.get("subscriber_count", 0),
                "niche":           lead.get("niche", niche_key),
                "location":        lead.get("location", ""),
                "score":           lead.get("score", 0),
                "score_reason":    lead.get("score_reason", ""),
            })

            sent += 1
            print(f"       Sent from {account['email']} (score {lead['score']}/7)")

            if i < len(qualified) - 1:
                print(f"       Waiting {EMAIL_ROTATION_DELAY}s…")
                time.sleep(EMAIL_ROTATION_DELAY)

        except Exception as e:
            print(f"       FAILED — {e}")

    # 4. Send report
    ts = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    report = f"""Lead Generation Complete — v3

{ts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAMPAIGN SUMMARY

Channels scraped     : {len(raw_channels)}
Qualified by code    : {len(qualified)}
Emails sent          : {sent}
Duplicates skipped   : {skipped}
YouTube API used     : #{used_api}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW LEADS WERE QUALIFIED (no Claude scoring)

  REQUIRED  Email found in description or any video description
  REQUIRED  Last video posted within 90 days
  SOFT      Subscriber count (pre-filtered in search)
  SOFT      Location (email presence overrides mismatch)
  SOFT      Niche (matched by search keyword already)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS

  1. Run python followup.py tomorrow for Day-2 follow-ups
  2. Monitor replies in Gmail
  3. Check Notion for all lead details

© Fuelvia System v3"""

    send_report_email(
        "Fuelviaa01@gmail.com",
        f"Lead Generation Complete — {sent} emails sent",
        report,
    )

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)
    print(f"\n  {len(raw_channels)} channels scraped")
    print(f"  {len(qualified)} qualified by code (email + active)")
    print(f"  {sent} personalized emails sent via Claude")
    print(f"  {skipped} duplicates skipped")
    print(f"  Report sent to Fuelviaa01@gmail.com\n")


if __name__ == "__main__":
    main()
