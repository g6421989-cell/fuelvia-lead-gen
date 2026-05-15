"""
FUELVIA LEAD GENERATION v2 - GOD MODE UPGRADE
==============================================

Multi-keyword search + Intelligent local scoring (NO Claude scoring!)
- 7 keywords × 4 locations = 28 searches (vs 1 before)
- Smart scorer based on REAL YouTube data
- 50-100+ qualified leads per run
- Quota: ~11,000 units/day (of 40k available)

USAGE: python generate_v2.py
"""

import re
import time
from datetime import datetime
from googleapiclient.discovery import build

from config import (
    YOUTUBE_APIS, NICHE_SEARCH_TERMS, NICHE_OPTIONS, LOCATION_OPTIONS,
    SUBSCRIBER_RANGES, EMAIL_ROTATION_DELAY, SENDER_NAME, COMPANY_NAME
)
from notion_manager import NotionManager
from email_helpers import EmailRotator, send_report_email
from claude_helpers import write_personalized_initial_email
from youtube_enricher import enrich_channel_data, batch_enrich_channels
from smart_scorer import intelligent_score_channel
from cta_detector import parse_pricing

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
EXCLUDED_DOMAINS = {"example.com", "youremail.com", "gmail.com", "email.com", "noreply.com"}


def print_banner():
    """Print system banner"""
    print("\n" + "=" * 70)
    print("   🔥 FUELVIA LEAD GENERATION v2.0 - GOD MODE 🔥")
    print("   Multi-keyword search + Intelligent local scoring")
    print("=" * 70 + "\n")


def select_option(prompt, options):
    """Display menu and get user choice"""
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
        print(f"  Please enter a number between 1 and {len(options)}")


def get_user_inputs():
    """Get user preferences"""
    print_banner()

    # Niche selection
    niche = select_option("📌 NICHE OPTIONS:", NICHE_OPTIONS)
    if niche == "Custom":
        niche = input("  Enter custom search terms (comma-separated): ").strip()
        niche = niche.split(",")
    else:
        niche = NICHE_SEARCH_TERMS.get(niche, [niche])

    # Location selection (now returns list)
    location_options = list(LOCATION_OPTIONS.keys())
    location_key = select_option("🌍 LOCATION:", location_options)
    location_list = LOCATION_OPTIONS[location_key]

    # Subscriber range
    range_keys = list(SUBSCRIBER_RANGES.keys())
    sub_range_key = select_option("👥 SUBSCRIBER RANGE:", range_keys)
    sub_range = SUBSCRIBER_RANGES[sub_range_key]

    # Lead count
    while True:
        try:
            count = input("\n🔢 How many leads to scrape? (default: 50): ").strip()
            count = int(count) if count else 50
            break
        except ValueError:
            print("  Please enter a valid number.")

    return niche, location_list, sub_range, count


def extract_email_from_text(text):
    """Extract email from text"""
    if not text:
        return None
    matches = EMAIL_REGEX.findall(text)
    for email in matches:
        domain = email.split("@")[1].lower()
        if domain not in EXCLUDED_DOMAINS:
            return email.lower()
    return None


def get_youtube_client(api_index=0):
    """Get YouTube client with API key rotation"""
    api_key = YOUTUBE_APIS[api_index % len(YOUTUBE_APIS)]
    return build("youtube", "v3", developerKey=api_key), api_index


def get_channel_details(youtube, channel_id):
    """Get basic channel info"""
    try:
        resp = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()
        if not resp.get("items"):
            return None
        item = resp["items"][0]
        desc = item["snippet"].get("description", "")
        subs = int(item["statistics"].get("subscriberCount", 0))
        email = extract_email_from_text(desc)
        return {
            "channel_name": item["snippet"]["title"],
            "email": email,
            "subscriber_count": subs,
            "youtube_url": f"https://youtube.com/channel/{channel_id}",
            "description": desc[:500],  # Longer desc for scoring
            "channel_id": channel_id,
        }
    except Exception:
        return None


def scrape_youtube_multi_keyword(niche_keywords, location_list, sub_range, max_leads):
    """
    Multi-keyword, multi-location YouTube search
    Searches each keyword × location combination
    """
    api_index = 0
    youtube, api_index = get_youtube_client(api_index)

    location_terms = location_list if isinstance(location_list, list) else [location_list]
    sub_min, sub_max = sub_range

    print(f"\n🔍 MULTI-KEYWORD SEARCH")
    print(f"   Keywords: {len(niche_keywords)}")
    print(f"   Locations: {len(location_terms)}")
    print(f"   Target: {max_leads * 3} channels (~{max_leads} qualified)\n")

    raw_channels = []
    seen_channel_ids = set()
    total_searches = 0

    # Search each keyword × location combination
    for keyword in niche_keywords:
        for location_term in location_terms:
            total_searches += 1

            # Build query
            if location_term:
                query = f"{keyword} {location_term}".strip()
            else:
                query = keyword

            print(f"  🔎 [{total_searches}] Searching: '{query}'...")

            next_page = None
            pages_fetched = 0
            max_pages = 3  # Get 3 pages per keyword (50 results each)

            while pages_fetched < max_pages and len(raw_channels) < max_leads * 3:
                try:
                    params = {
                        "part": "snippet",
                        "q": query,
                        "type": "channel",
                        "maxResults": 50,
                        "relevanceLanguage": "en"
                    }
                    if next_page:
                        params["pageToken"] = next_page

                    resp = youtube.search().list(**params).execute()
                    items = resp.get("items", [])

                    if not items:
                        break

                    # Process each channel
                    for item in items:
                        channel_id = item["snippet"]["channelId"]

                        # Skip duplicates
                        if channel_id in seen_channel_ids:
                            continue

                        # Get full details
                        details = get_channel_details(youtube, channel_id)
                        if not details:
                            continue

                        subs = details["subscriber_count"]

                        # Filter by subscriber range
                        if subs < sub_min or (sub_max and subs > sub_max):
                            continue

                        # CRITICAL: Skip if no email (don't waste Notion space)
                        if not details.get("email"):
                            continue

                        # Add metadata
                        details["niche"] = " + ".join(niche_keywords)
                        details["location"] = location_term if location_term else "Global"

                        raw_channels.append(details)
                        seen_channel_ids.add(channel_id)

                    next_page = resp.get("nextPageToken")
                    if not next_page:
                        break

                    pages_fetched += 1
                    time.sleep(0.5)  # Rate limit

                except Exception as e:
                    if "quotaExceeded" in str(e) or "403" in str(e):
                        print(f"    ⚠️  API quota exceeded. Rotating API...")
                        api_index = (api_index + 1) % len(YOUTUBE_APIS)
                        youtube, api_index = get_youtube_client(api_index)
                    else:
                        print(f"    ❌ Error: {e}")
                    break

            print(f"       Found {len(raw_channels)} total so far...")
            time.sleep(0.5)

    print(f"\n📡 SEARCH COMPLETE")
    print(f"   Total searches: {total_searches}")
    print(f"   Unique channels found: {len(raw_channels)}")
    print(f"   Channels with emails: {len(raw_channels)} (filtered already)")
    print()

    return raw_channels, youtube, api_index


def analyze_and_filter_leads(raw_channels, youtube, max_leads):
    """
    Enrich channels with YouTube data
    Score using intelligent algorithm (NOT Claude)
    Filter to qualified leads
    """
    print(f"📊 INTELLIGENT SCORING (No Claude needed!)\n")

    # Batch enrich with video data
    print(f"  📺 Fetching video data ({len(raw_channels)} channels)...\n")
    enriched = batch_enrich_channels(
        youtube,
        raw_channels,
        fetch_video_stats=True,
        rate_limit_delay=0.3
    )

    qualified = []
    scoring_details = []

    print(f"\n  🧠 Scoring with smart algorithm...\n")

    for i, channel in enumerate(enriched):
        if len(qualified) >= max_leads:
            break

        channel_name = channel.get('channel_name', '')
        print(f"  [{i+1}/{len(enriched)}] Analyzing: {channel_name}...")

        # Score using intelligent algorithm
        videos_data = channel.get('videos_data', [])
        days_since = channel.get('days_since_last_video', 999)

        analysis = intelligent_score_channel(channel, videos_data, days_since)

        channel["score"] = analysis["score"]
        channel["score_reason"] = analysis["reason"]
        channel["confidence"] = analysis.get("confidence", 70)

        # Print scoring details
        score_display = f"{analysis['score']}/10"
        conf = f"{analysis['confidence']}% confident"

        if analysis["qualified"]:
            qualified.append(channel)
            print(f"      ✅ QUALIFIED ({score_display}, {conf})")
        else:
            reason = analysis.get("reason", "Low score")
            print(f"      ❌ SKIP ({score_display}) - {reason}")

        # Store details for report
        scoring_details.append({
            "channel_name": channel_name,
            "score": analysis["score"],
            "qualified": analysis["qualified"],
            "reasons": analysis.get("reasons", [])
        })

    print(f"\n  📊 Scoring Summary")
    print(f"     Total analyzed: {len(enriched)}")
    print(f"     Qualified: {len(qualified)}")
    print(f"     Pass rate: {len(qualified) / len(enriched) * 100:.1f}%\n")

    return qualified, scoring_details


def main():
    """Main execution"""
    niche_keywords, location_list, sub_range, max_leads = get_user_inputs()

    print("\n" + "=" * 70)
    print("🚀 Starting Multi-Keyword Lead Generation...")
    print("=" * 70 + "\n")

    # Scrape YouTube with multiple keywords
    raw_channels, youtube, used_api = scrape_youtube_multi_keyword(
        niche_keywords, location_list, sub_range, max_leads
    )

    if not raw_channels:
        print("❌ No channels found. Try different search terms.\n")
        return

    # Analyze and filter with intelligent scoring
    qualified_leads, scoring_details = analyze_and_filter_leads(
        raw_channels, youtube, max_leads
    )

    if not qualified_leads:
        print("❌ No qualified leads found. Try broader search terms.\n")
        return

    # Initialize managers
    notion = NotionManager()
    rotator = EmailRotator()

    print(f"\n📧 Sending personalized emails ({len(qualified_leads)} leads)...\n")

    emails_sent = 0
    for i, lead in enumerate(qualified_leads):
        # Check duplicate
        is_dup, _ = notion.check_duplicate(lead["email"])
        if is_dup:
            print(f"  ⏭️  Skipping duplicate: {lead['channel_name']}")
            continue

        # Write personalized email using Claude (it's good at this!)
        print(f"  ✍️  Writing email for {lead['channel_name']}...")
        subject, body = write_personalized_initial_email(lead, {
            "score": lead.get("score", 5),
            "reason": lead.get("score_reason", "")
        })

        # Send from rotated account
        account = rotator.get_next_account()

        msg_subject = f"{subject}"
        msg_body = f"{body}"

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = f"{SENDER_NAME} - {COMPANY_NAME} <{account['email']}>"
            msg["To"] = lead["email"]
            msg["Subject"] = msg_subject
            msg.attach(MIMEText(msg_body, "plain"))

            with smtplib.SMTP(account["smtp_server"], account["smtp_port"]) as server:
                server.starttls()
                server.login(account["email"], account["password"])
                server.sendmail(account["email"], lead["email"], msg.as_string())

            # Add to Notion
            notion.create_lead({
                "channel_name": lead["channel_name"],
                "email": lead["email"],
                "youtube_url": lead["youtube_url"],
                "subscriber_count": lead["subscriber_count"],
                "niche": " + ".join(niche_keywords) if isinstance(niche_keywords, list) else niche_keywords,
                "location": lead.get("location", ""),
                "score": lead["score"],
                "score_reason": lead["score_reason"]
            })

            emails_sent += 1
            print(f"  ✅ [{emails_sent}/{len(qualified_leads)}] Sent to {lead['channel_name']} (Score: {lead['score']}/10)")

            # Wait before next email
            if i < len(qualified_leads) - 1:
                time.sleep(EMAIL_ROTATION_DELAY)

        except Exception as e:
            print(f"  ❌ Failed to send to {lead['email']}: {e}")

    # Send report
    print(f"\n📨 Sending report...\n")

    report_body = f"""🔥 FUELVIA LEAD GENERATION v2.0 - COMPLETE!

═══════════════════════════════════════════════════════════════

📊 CAMPAIGN SUMMARY

Total channels analyzed: {len(raw_channels)}
Channels with emails: {len(raw_channels)}
Qualified (score 5+/10): {len(qualified_leads)}
Emails sent: {emails_sent}
YouTube API used: #{used_api}
Timestamp: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

═══════════════════════════════════════════════════════════════

🎯 SEARCH STRATEGY

Keywords searched: {len(niche_keywords)}
Locations searched: {len(location_list)}
Total searches: {len(niche_keywords) * len(location_list)}

═══════════════════════════════════════════════════════════════

✨ SMART SCORING (No Claude Guesses!)

✅ Scored based on REAL YouTube data:
   - Recent upload frequency
   - Video engagement (views, likes, comments)
   - Clear CTAs in titles/descriptions
   - B2B language patterns
   - Audience engagement metrics
   - Pricing indicators

Pass rate: {len(qualified_leads) / len(raw_channels) * 100:.1f}%

═══════════════════════════════════════════════════════════════

📈 QUOTA USAGE

Daily available: 40,000 units (4 APIs × 10k each)
Used this run: ~{len(raw_channels) * 5 + len(raw_channels) * 100 / 50} units
Remaining: ~{40000 - (len(raw_channels) * 5 + len(raw_channels) * 100 / 50)} units

═══════════════════════════════════════════════════════════════

✅ All leads have been added to Notion.

NEXT STEPS:
1. Run 'python followup.py' tomorrow to send Day 2 follow-ups
2. Monitor replies in your Gmail inbox
3. Check Notion for lead details and confidence scores

© Fuelvia System - v2.0 GOD MODE UPGRADE 🚀"""

    send_report_email(
        "Fuelviaa01@gmail.com",
        f"🔥 Lead Generation Complete v2 - {emails_sent} Emails Sent",
        report_body
    )

    print("\n" + "=" * 70)
    print("🎉 LEAD GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\n  ✅ {len(raw_channels)} channels analyzed")
    print(f"  ✅ {len(qualified_leads)} qualified (score 5+/10)")
    print(f"  ✅ {emails_sent} personalized emails sent")
    print(f"  ✅ All data saved to Notion")
    print(f"  ✅ Report sent to Fuelviaa01@gmail.com\n")


if __name__ == "__main__":
    main()
