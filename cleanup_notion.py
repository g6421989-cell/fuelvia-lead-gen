#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTION CLEANUP - Remove all non-New leads
============================================================
Deletes leads with status: Contacted, Follow-up 1, blank, etc.
Keeps ONLY leads with status: New
============================================================
"""

import sys
import io
import requests

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config import NOTION_API_KEY, NOTION_DATABASE_ID

BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


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


def delete_page(page_id):
    """Archive a page (lead) from Notion database."""
    # Use the pages endpoint, not blocks
    url = f"{BASE_URL}/pages/{page_id}"
    payload = {"archived": True}

    try:
        resp = requests.patch(url, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to archive {page_id}: {e}")
        return False


def extract_status(record):
    """Extract status from Notion record."""
    try:
        if record is None or not isinstance(record, dict):
            return None
        props = record.get("properties") or {}
        status_field = props.get("Status") or {}
        status = status_field.get("select") or {}
        return status.get("name") or None
    except:
        return None


def main():
    print("\n" + "="*60)
    print("  NOTION CLEANUP - Remove non-New leads")
    print("="*60 + "\n")

    print("[1/3] Fetching all leads from Notion...")
    records = get_all_leads()

    if not records:
        print("[ERROR] No records found")
        return

    print(f"[OK] Found {len(records)} total records\n")

    # Categorize leads
    new_leads = []
    to_delete = []

    for r in records:
        try:
            status = extract_status(r)
            page_id = r.get("id")
            channel_name = "Unknown"

            # Try to get channel name
            props = r.get("properties") or {}
            channel_field = props.get("Channel Name") or {}
            title_list = channel_field.get("title") or []
            if title_list and len(title_list) > 0:
                channel_name = title_list[0].get("text", {}).get("content", "Unknown")

            if status == "New":
                new_leads.append(page_id)
                print(f"  [KEEP] {channel_name} (Status: New)")
            else:
                to_delete.append((page_id, channel_name, status))
                print(f"  [DELETE] {channel_name} (Status: {status or 'BLANK'})")
        except Exception as e:
            pass  # Silently skip encoding errors

    print(f"\n[2/3] Summary:")
    print(f"  Leads to KEEP (New):     {len(new_leads)}")
    print(f"  Leads to DELETE (other): {len(to_delete)}\n")

    if not to_delete:
        print("[OK] No leads to delete - database is clean!")
        return

    # Delete without prompting
    print("[3/3] Deleting non-New leads...")

    deleted = 0
    failed = 0

    for page_id, channel_name, status in to_delete:
        if delete_page(page_id):
            print(f"  [OK] Deleted: {channel_name} (was: {status or 'BLANK'})")
            deleted += 1
        else:
            print(f"  [ERROR] Failed: {channel_name}")
            failed += 1

    print(f"\n" + "="*60)
    print(f"  CLEANUP COMPLETE")
    print(f"="*60)
    print(f"  Deleted:         {deleted}")
    print(f"  Failed:          {failed}")
    print(f"  Remaining (New): {len(new_leads)}")
    print(f"="*60 + "\n")


if __name__ == "__main__":
    main()
