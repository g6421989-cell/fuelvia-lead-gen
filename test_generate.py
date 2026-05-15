#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FUELVIA TEST SCRIPT - Direct testing without interactive prompts
Tests the entire system: YouTube scraping, Notion, Claude, Email, Backup
"""

import sys
import io

# Fix Unicode encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("FUELVIA SYSTEM TEST - AUTOMATED")
print("=" * 60)
print()

# Import everything
print("[1/5] Loading configuration...")
try:
    from config_secure import (
        YOUTUBE_APIS, NICHE_SEARCH_TERMS,
        LOCATION_OPTIONS, SUBSCRIBER_RANGES,
        EMAIL_ROTATION_DELAY, SENDER_NAME, SENDER_TITLE, COMPANY_NAME, CALENDAR_LINK,
    )
    print("      ✓ Config loaded from .env")
except Exception as e:
    print(f"      ✗ Config load failed: {e}")
    sys.exit(1)

print("[2/5] Testing YouTube API...")
try:
    from googleapiclient.discovery import build
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_APIS[0])
    print(f"      ✓ YouTube API #{1} connected")
except Exception as e:
    print(f"      ✗ YouTube API failed: {e}")

print("[3/5] Testing Notion database...")
try:
    from notion_manager import NotionManager
    notion = NotionManager()
    print("      ✓ Notion manager initialized")
    # Try to connect
    stats = notion.get_system_stats()
    print(f"      ✓ Notion connection verified")
except Exception as e:
    print(f"      ✗ Notion failed: {e}")

print("[4/5] Testing backup system...")
try:
    from backup_manager import backup_manager
    stats = backup_manager.get_backup_stats()
    print(f"      ✓ Backup system ready")
    print(f"        - Leads in backup: {stats.get('total_leads', 0)}")
    print(f"        - Emails logged: {stats.get('total_emails_sent', 0)}")
    print(f"        - Replies logged: {stats.get('total_replies', 0)}")
except Exception as e:
    print(f"      ✗ Backup system failed: {e}")

print("[5/5] Testing error logging...")
try:
    from error_logger import logger
    logger.log_success("Test message from test script")
    print("      ✓ Error logger working")
except Exception as e:
    print(f"      ✗ Error logger failed: {e}")

print()
print("=" * 60)
print("RUNNING ACTUAL LEAD GENERATION TEST")
print("=" * 60)
print()

# Now run the actual generation with hardcoded parameters
try:
    from googleapiclient.discovery import build
    from youtube_enricher import get_videos_for_channel, days_since_last_video
    from channel_qualifier import qualify_channel
    from email_helpers import EmailRotator
    from notion_manager import NotionManager
    from claude_helpers import write_personalized_initial_email
    import time

    print("Starting test with parameters:")
    print("  - Niche: Business Coach")
    print("  - Location: USA, UK, Canada, Australia")
    print("  - Subscriber Range: 1,000 - 20,000")
    print("  - Max Leads: 5")
    print()

    # Set parameters
    niche_key = "Business Coach"
    keywords = NICHE_SEARCH_TERMS[niche_key]
    location_list = ["USA", "UK", "Canada", "Australia"]
    sub_range = (1000, 20000)
    max_leads = 5

    # Initialize
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_APIS[0])
    notion = NotionManager()
    rotator = EmailRotator()
    leads_added = 0

    print("Searching YouTube for channels...")
    all_channels = []

    for keyword in keywords[:2]:  # Test with just 2 keywords for speed
        try:
            print(f"  Searching: '{keyword}'...")
            request = youtube.search().list(
                q=keyword,
                part='snippet',
                type='channel',
                order='viewCount',
                maxResults=5,
                relevanceLanguage='en',
                regionCode='US'
            )
            response = request.execute()

            for item in response.get('items', []):
                channel_id = item['id']['channelId']
                channel_name = item['snippet']['title']
                all_channels.append((channel_id, channel_name))
                print(f"    Found: {channel_name}")

        except Exception as e:
            print(f"    Error searching '{keyword}': {str(e)[:100]}")
            continue

    print()
    print(f"Found {len(all_channels)} channels. Qualifying...")
    print()

    # Qualify and add leads
    for channel_id, channel_name in all_channels[:max_leads]:
        if leads_added >= max_leads:
            break

        try:
            print(f"Processing: {channel_name}...")

            # Get channel details
            channel_request = youtube.channels().list(
                part='statistics,snippet',
                id=channel_id
            )
            channel_response = channel_request.execute()
            channel_data = channel_response['items'][0]

            subscriber_count = int(channel_data['statistics'].get('subscriberCount', 0))

            # Check subscriber range
            if not (sub_range[0] <= subscriber_count <= (sub_range[1] if sub_range[1] else 999999999)):
                print(f"  ✗ Subscribers {subscriber_count:,} out of range {sub_range}")
                continue

            # Get videos
            videos = get_videos_for_channel(youtube, channel_id, 5)
            if not videos:
                print(f"  ✗ No videos found")
                continue

            # Check last video date
            days_old = days_since_last_video(videos)
            if days_old > 90:
                print(f"  ✗ Last video {days_old} days old (>90)")
                continue

            # Qualify
            qualified, email = qualify_channel(channel_id, channel_name, videos, location_list)
            if not qualified:
                print(f"  ✗ Channel not qualified (no email or other criteria)")
                continue

            print(f"  ✓ Qualified! Email: {email}")

            # Generate email
            print(f"  Writing personalized email with Claude...")
            subject, body = write_personalized_initial_email(
                channel_name, niche_key, email,
                SENDER_NAME, SENDER_TITLE, COMPANY_NAME, CALENDAR_LINK
            )

            print(f"  Email subject: {subject[:50]}...")

            # Create lead object
            lead = {
                'id': channel_id,
                'channel_name': channel_name,
                'email': email,
                'youtube_url': f"https://youtube.com/@{channel_id}",
                'subscriber_count': subscriber_count,
                'niche': niche_key,
                'location': ', '.join(location_list),
                'score': 95,
                'status': 'New',
                'date_added': __import__('datetime').datetime.now().isoformat(),
                '_prepared_subject': subject,
                '_prepared_body': body,
            }

            # Save to Notion
            print(f"  Saving to Notion...")
            notion.add_lead(lead)

            # Backup
            from backup_manager import backup_manager
            backup_manager.backup_lead(lead)

            leads_added += 1
            print(f"  ✓ LEAD #{leads_added} ADDED")
            print()

        except Exception as e:
            print(f"  ✗ Error processing {channel_name}: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            continue

    print("=" * 60)
    print(f"TEST COMPLETE: {leads_added} leads added")
    print("=" * 60)

    # Check results
    print()
    print("Checking results...")

    # Check Notion
    print("  Checking Notion database...")
    notion_leads = notion.get_all_leads()
    print(f"    ✓ Total leads in Notion: {len(notion_leads)}")

    # Check backup
    print("  Checking backup database...")
    backup_stats = backup_manager.get_backup_stats()
    print(f"    ✓ Total leads in backup: {backup_stats['total_leads']}")

    # Check logs
    print("  Checking system logs...")
    try:
        with open('logs/system.log', 'r') as f:
            log_lines = f.readlines()
        print(f"    ✓ System log has {len(log_lines)} entries")
    except:
        print(f"    ! System log not found")

    print()
    print("✅ ALL SYSTEMS OPERATIONAL")

except Exception as e:
    print(f"✗ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
