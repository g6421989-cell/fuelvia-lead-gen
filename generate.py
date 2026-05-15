"""
FUELVIA LEAD GENERATION v3
===========================
Code qualifies leads. Claude writes emails. No Claude scoring.

Qualification rules (pure Python):
  REQUIRED  email found in channel description OR any of last 5 video descriptions
  REQUIRED  last video posted within 90 days
  SOFT      subscriber count  (pre-filtered by search)
  SOFT      location          (email presence overrides mismatch)
  SOFT      niche             (matched by search keyword already)

USAGE: python generate.py
"""

# -*- coding: utf-8 -*-
import sys
import io

# Fix Unicode encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re
import time
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build

from config_secure import (
    YOUTUBE_APIS, NICHE_OPTIONS, NICHE_SEARCH_TERMS,
    LOCATION_OPTIONS, SUBSCRIBER_RANGES,
    EMAIL_ROTATION_DELAY, SENDER_NAME, SENDER_TITLE, COMPANY_NAME, CALENDAR_LINK,
)
from notion_manager import NotionManager
from email_helpers import EmailRotator, send_report_email
from claude_helpers import write_personalized_initial_email
from youtube_enricher import get_videos_for_channel, days_since_last_video
from channel_qualifier import qualify_channel


# ── UI ────────────────────────────────────────────────────────

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
    print("\n" + "=" * 60)
    print("   FUELVIA LEAD GENERATION SYSTEM")
    print("=" * 60 + "\n")

    niche_key = select_option("📌 NICHE:", NICHE_OPTIONS)
    if niche_key == "Custom":
        raw = input("  Enter keywords (comma-separated): ").strip()
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
    else:
        keywords = NICHE_SEARCH_TERMS.get(niche_key, [niche_key])

    location_key = select_option("🌍 LOCATION:", list(LOCATION_OPTIONS.keys()))
    location_list = LOCATION_OPTIONS[location_key]

    sub_range_key = select_option("👥 SUBSCRIBER RANGE:", list(SUBSCRIBER_RANGES.keys()))
    sub_range = SUBSCRIBER_RANGES[sub_range_key]

    while True:
        try:
            raw_n = input("\n🔢 How many leads? (default 50): ").strip()
            max_leads = int(raw_n) if raw_n else 50
            break
        except ValueError:
            print("  Enter a valid number.")

    return niche_key, keywords, location_list, sub_range, max_leads


# ── YOUTUBE ───────────────────────────────────────────────────

def get_youtube_client(api_index=0):
    key = YOUTUBE_APIS[api_index % len(YOUTUBE_APIS)]
    return build("youtube", "v3", developerKey=key), api_index


_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
_SKIP_DOMAINS = {"example.com", "youremail.com", "gmail.com", "email.com", "noreply.com"}


def get_channel_details(youtube, channel_id):
    try:
        resp = youtube.channels().list(
            part="snippet,statistics,contentDetails", id=channel_id
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        item = items[0]
        desc = item["snippet"].get("description", "")
        subs = int(item["statistics"].get("subscriberCount", 0))
        # uploads playlist ID — used by youtube_enricher to avoid costly search()
        uploads_pl = (
            item.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads", None)
        )
        return {
            "channel_name":        item["snippet"]["title"],
            "subscriber_count":    subs,
            "description":         desc,
            "youtube_url":         f"https://youtube.com/channel/{channel_id}",
            "channel_id":          channel_id,
            "uploads_playlist_id": uploads_pl,   # free — already in channels.list
        }
    except Exception:
        return None


def scrape_youtube(keywords, location_list, sub_range, max_leads):
    api_index = 0
    youtube, api_index = get_youtube_client(api_index)
    sub_min, sub_max = sub_range
    seen_ids = set()
    raw = []
    n = 0

    print(f"\n🔍 Searching {len(keywords)} keyword(s) × {len(location_list)} location(s)...\n")

    for keyword in keywords:
        for loc in location_list:
            n += 1
            query = f"{keyword} {loc}".strip() if loc else keyword
            print(f"  [{n:02d}] '{query}'")

            next_page = None
            pages = 0

            while pages < 3:
                try:
                    params = {
                        "part": "snippet", "q": query,
                        "type": "channel", "maxResults": 50,
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
                        print(f"       ⚠️  quota hit — rotating API key")
                        api_index = (api_index + 1) % len(YOUTUBE_APIS)
                        youtube, api_index = get_youtube_client(api_index)
                    else:
                        print(f"       ❌ {e}")
                    break

            print(f"       total so far: {len(raw)}")
            time.sleep(0.3)

    print(f"\n  📡 {len(raw)} unique channels found in subscriber range\n")
    return raw, youtube, api_index


# ── QUALIFY ───────────────────────────────────────────────────

def enrich_and_qualify(raw_channels, youtube_client, api_index, max_leads):
    """
    Per channel (cost: ~3 API units each):
      1. playlistItems.list  → last 5 video IDs + dates  (1 unit)
      2. videos.list         → titles, descriptions, stats  (1 unit)
      3. days_since_last_video from returned dates  (0 units)
      4. Extract email from channel desc + all video descs  (0 units)
      5. Qualify: email exists AND last post ≤ 90 days  (0 units)
      6. Score 0-7 for sort priority  (0 units)

    Rotates API key automatically on quota errors.
    """
    print("🔎 Fetching video data + qualifying...\n")

    youtube    = youtube_client
    qualified  = []
    no_email   = inactive = 0

    for i, ch in enumerate(raw_channels):
        name         = ch.get("channel_name", "?")
        cid          = ch.get("channel_id", "")
        uploads_pl   = ch.get("uploads_playlist_id")

        print(f"  [{i+1:03d}/{len(raw_channels)}] {name}")

        # Fetch last 5 videos — rotate API key on quota error
        videos = []
        for attempt in range(len(YOUTUBE_APIS)):
            try:
                videos = get_videos_for_channel(
                    youtube,
                    cid,
                    uploads_playlist_id=uploads_pl,
                    max_videos=5,
                )
                break
            except Exception as e:
                if "quotaExceeded" in str(e) or "403" in str(e):
                    api_index = (api_index + 1) % len(YOUTUBE_APIS)
                    youtube, api_index = get_youtube_client(api_index)
                    print(f"       ⚠️  quota hit — rotated to API #{api_index}")
                else:
                    print(f"       ⚠️  video fetch error: {e}")
                    break

        # Days since last post — derived from video data, costs 0 extra units
        days = days_since_last_video(videos)

        ch["days_since_last_video"] = days
        ch["videos_data"]           = videos

        result = qualify_channel(ch, videos, days)

        if not result["qualified"]:
            reason = result["reason"]
            print(f"       SKIP — {reason}")
            if "No email" in reason:
                no_email += 1
            else:
                inactive += 1
            continue

        ch["email"]        = result["email"]
        ch["score"]        = result["score"]
        ch["score_reason"] = result["reason"]

        qualified.append(ch)

        src = " (video desc)" if result.get("email_source") == "video_desc" else ""
        print(f"       ✅ QUALIFIED score {result['score']}/7 | {result['email']}{src}")

        if len(qualified) >= max_leads:
            print(f"\n  Target of {max_leads} reached.\n")
            break

        time.sleep(0.2)

    qualified.sort(key=lambda c: c["score"], reverse=True)

    checked = i + 1
    print(f"\n  📊 Checked: {checked}  |  No email: {no_email}  |  Inactive: {inactive}  |  Qualified: {len(qualified)}\n")
    return qualified, api_index


# ── MAIN ──────────────────────────────────────────────────────

def main():
    niche_key, keywords, location_list, sub_range, max_leads = get_user_inputs()

    print("\n" + "=" * 60)
    print("🚀 Starting Lead Generation...")
    print("=" * 60)

    raw_channels, youtube, api_index = scrape_youtube(
        keywords, location_list, sub_range, max_leads
    )

    if not raw_channels:
        print("\n❌ No channels found. Try broader search terms.\n")
        return

    qualified, used_api = enrich_and_qualify(raw_channels, youtube, api_index, max_leads)

    if not qualified:
        print("\n❌ No qualified leads. Try broader search terms or wider subscriber range.\n")
        return

    notion  = NotionManager()
    rotator = EmailRotator()
    sent = skipped = 0

    print(f"📧 Sending personalized emails ({len(qualified)} leads)...\n")

    for i, lead in enumerate(qualified):
        name  = lead["channel_name"]
        email = lead["email"]

        is_dup, _ = notion.check_duplicate(email)
        if is_dup:
            print(f"  ⏭️  Duplicate: {name}")
            skipped += 1
            continue

        # Use pre-written email if available, otherwise write now
        if "_prepared_subject" in lead and "_prepared_body" in lead:
            print(f"  ✅ Using pre-written email for {name}...")
            subject = lead["_prepared_subject"]
            body = lead["_prepared_body"]
        else:
            print(f"  ✍️  Writing email for {name}...")
            subject, body = write_personalized_initial_email(
                lead,
                lead.get("videos_data", []),
            )

        account = rotator.get_next_account()
        try:
            msg = MIMEMultipart()
            msg["From"]    = f"{SENDER_NAME}, {SENDER_TITLE} <{account['email']}>"
            msg["To"]      = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(account["smtp_server"], account["smtp_port"]) as srv:
                srv.starttls()
                srv.login(account["email"], account["password"])
                srv.sendmail(account["email"], email, msg.as_string())

            notion.create_lead({
                "channel_name":     name,
                "email":            email,
                "youtube_url":      lead.get("youtube_url", ""),
                "subscriber_count": lead.get("subscriber_count", 0),
                "niche":            lead.get("niche", niche_key),
                "location":         lead.get("location", ""),
                "score":            lead.get("score", 0),
                "score_reason":     lead.get("score_reason", ""),
            })

            sent += 1
            print(f"  ✅ [{sent}] {name} (score {lead['score']}/7) via {account['email']}")

            # While waiting, write next email in parallel
            if i < len(qualified) - 1:
                next_lead = qualified[i + 1]
                next_name = next_lead["channel_name"]

                # Skip duplicates from being pre-written
                is_next_dup, _ = notion.check_duplicate(next_lead["email"])

                print(f"  ⏳ Waiting {EMAIL_ROTATION_DELAY}s (Claude writing next email)...")
                start_time = time.time()

                # Write next email while clock is running
                if not is_next_dup and "_prepared_subject" not in next_lead:
                    print(f"     ✍️  Preparing email for {next_name}...")
                    next_subject, next_body = write_personalized_initial_email(
                        next_lead,
                        next_lead.get("videos_data", []),
                    )
                    next_lead["_prepared_subject"] = next_subject
                    next_lead["_prepared_body"] = next_body
                    print(f"     ✅ Email ready for {next_name}")

                # Wait for remaining time
                elapsed = time.time() - start_time
                remaining = EMAIL_ROTATION_DELAY - elapsed
                if remaining > 0:
                    time.sleep(remaining)

        except Exception as e:
            print(f"  ❌ Failed — {e}")

    # Report
    ts = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    send_report_email(
        "Fuelviaa01@gmail.com",
        f"✅ Lead Generation Complete — {sent} Emails Sent",
        f"""Lead Generation Complete!

{ts}

Channels scraped   : {len(raw_channels)}
Qualified          : {len(qualified)}
Emails sent        : {sent}
Duplicates skipped : {skipped}
YouTube API used   : #{used_api}

Qualification method: Code only (email + active ≤90 days)
Claude used for    : Email writing only

Next steps:
1. Run python followup.py tomorrow for Day-2 follow-ups
2. Check Notion for all leads
3. Monitor Gmail for replies

© Fuelvia System""",
    )

    print("\n" + "=" * 60)
    print("🎉 DONE!")
    print("=" * 60)
    print(f"\n  ✅ {len(raw_channels)} channels scraped")
    print(f"  ✅ {len(qualified)} qualified (email + active)")
    print(f"  ✅ {sent} emails sent")
    print(f"  ✅ Report sent to Fuelviaa01@gmail.com\n")


if __name__ == "__main__":
    main()
