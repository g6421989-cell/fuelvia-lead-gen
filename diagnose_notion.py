"""
DIAGNOSTIC SCRIPT - Check Notion database schema
Tells us the exact field names and types in your database
USAGE: python diagnose_notion.py
"""

import requests
from config import NOTION_API_KEY, NOTION_DATABASE_ID

def diagnose_database():
    """Check database schema"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    print("\n" + "=" * 70)
    print("  NOTION DATABASE DIAGNOSTIC")
    print("=" * 70 + "\n")

    # Get database info
    print(f"Database ID: {NOTION_DATABASE_ID}\n")

    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        print(f"❌ Error accessing database: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return

    db_info = resp.json()

    print("📋 DATABASE SCHEMA - Property Names & Types:\n")

    properties = db_info.get("properties", {})
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "unknown")
        print(f"  • {field_name:<30} → Type: {field_type}")

    print("\n" + "=" * 70)
    print("✅ Copy the EXACT field names above into notion_manager.py")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    diagnose_database()
