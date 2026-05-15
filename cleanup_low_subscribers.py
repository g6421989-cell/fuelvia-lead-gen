#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove all leads with fewer than 1,000 subscribers
Minimum subscriber range is 1,000 - ensure database is clean
"""

import sys
import io
import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config import NOTION_API_KEY, NOTION_DATABASE_ID

BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

MIN_SUBSCRIBERS = 1000  # Minimum allowed


def get_all_leads():
    """Fetch all leads from Notion database."""
    url = f"{BASE_URL}/databases/{NOTION_DATABASE_ID}/query"
    payload = {}

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch leads: {e}")
        return []


def get_subscriber_count(record):
    """Extract subscriber count from Notion record."""
    try:
        if record is None or not isinstance(record, dict):
            return None
        props = record.get("properties") or {}
        subs_field = props.get("Subscriber Count") or {}
        subs = subs_field.get("number") or 0
        return subs
    except:
        return None


def get_channel_name(record):
    """Extract channel name from Notion record."""
    try:
        if record is None or not isinstance(record, dict):
            return "Unknown"
        props = record.get("properties") or {}
        channel_field = props.get("Channel Name") or {}
        title_list = channel_field.get("title") or []
        if title_list and len(title_list) > 0:
            return title_list[0].get("text", {}).get("content", "Unknown")
        return "Unknown"
    except:
        return "Unknown"


def archive_page(page_id):
    """Archive a page (lead) from Notion database."""
    url = f"{BASE_URL}/pages/{page_id}"
    payload = {"archived": True}

    try:
        resp = requests.patch(url, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to archive {page_id}: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  Subscriber Count Cleanup - Remove < 1,000 subs")
    print("="*60 + "\n")

    print(f"[1/2] Fetching all leads from Notion...")
    records = get_all_leads()

    if not records:
        print("[ERROR] No records found")
        return

    print(f"[OK] Found {len(records)} total records\n")

    # Categorize by subscriber count
    valid = []
    to_delete = []

    for r in records:
        try:
            subs = get_subscriber_count(r)
            page_id = r.get("id")
            channel_name = get_channel_name(r)

            if subs is None:
                print(f"  [SKIP] {channel_name}: No subscriber count recorded")
                continue

            if subs < MIN_SUBSCRIBERS:
                to_delete.append((page_id, channel_name, subs))
                print(f"  [DELETE] {channel_name} ({subs} subs)")
            else:
                valid.append(page_id)
                print(f"  [KEEP] {channel_name} ({subs} subs)")
        except Exception as e:
            print(f"  [ERROR] Processing record: {e}")

    print(f"\n[2/2] Summary:")
    print(f"  Leads with >= {MIN_SUBSCRIBERS} subs: {len(valid)}")
    print(f"  Leads with < {MIN_SUBSCRIBERS} subs: {len(to_delete)}\n")

    if not to_delete:
        print("[OK] Database is clean - all leads have sufficient subscribers!")
        return

    # Delete low-subscriber leads
    print(f"Archiving {len(to_delete)} leads with low subscriber counts...\n")

    deleted = 0
    failed = 0

    for page_id, channel_name, subs in to_delete:
        if archive_page(page_id):
            print(f"  [OK] Archived: {channel_name} ({subs} subs)")
            deleted += 1
        else:
            print(f"  [ERROR] Failed: {channel_name}")
            failed += 1

    print(f"\n" + "="*60)
    print(f"  CLEANUP COMPLETE")
    print(f"="*60)
    print(f"  Archived:                {deleted}")
    print(f"  Failed:                  {failed}")
    print(f"  Remaining (>= {MIN_SUBSCRIBERS}): {len(valid)}")
    print(f"="*60 + "\n")


if __name__ == "__main__":
    main()
