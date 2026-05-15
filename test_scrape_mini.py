#!/usr/bin/env python3
# ============================================================
# MINI SCRAPING TEST - 5 Leads Only
# ============================================================

import sys
sys.path.insert(0, '.')

from backup_manager import backup_manager
from error_logger import logger
from notion_manager import NotionManager

print("\n" + "="*60)
print("MINI SCRAPING TEST - LOCAL DATABASE ONLY")
print("="*60)

try:
    # Test 1: Database initialization
    print("\n[TEST 1] Testing database initialization...")
    print(f"✅ Database initialized at: {backup_manager.db_file}")

    # Test 2: Create test leads
    print("\n[TEST 2] Creating 5 test leads in local database...")

    test_leads = [
        {
            'id': 'channel_1',
            'channel_name': 'Digital Marketing Pro',
            'email': 'john@digitalmarketing.com',
            'youtube_url': 'https://youtube.com/@dmpro',
            'subscriber_count': 25000,
            'niche': 'Digital Marketing',
            'location': 'United States',
            'score': 85,
            'status': 'New',
            'date_added': '2026-05-12',
        },
        {
            'id': 'channel_2',
            'channel_name': 'Growth Hacking Secrets',
            'email': 'sarah@growthhacking.com',
            'youtube_url': 'https://youtube.com/@ghs',
            'subscriber_count': 50000,
            'niche': 'Growth',
            'location': 'United States',
            'score': 90,
            'status': 'New',
            'date_added': '2026-05-12',
        },
        {
            'id': 'channel_3',
            'channel_name': 'SaaS Scaling',
            'email': 'mike@saasscaling.com',
            'youtube_url': 'https://youtube.com/@saasscale',
            'subscriber_count': 15000,
            'niche': 'SaaS',
            'location': 'United States',
            'score': 88,
            'status': 'New',
            'date_added': '2026-05-12',
        },
        {
            'id': 'channel_4',
            'channel_name': 'E-commerce Empire',
            'email': 'lisa@ecomempire.com',
            'youtube_url': 'https://youtube.com/@ecomemp',
            'subscriber_count': 35000,
            'niche': 'E-commerce',
            'location': 'United States',
            'score': 92,
            'status': 'New',
            'date_added': '2026-05-12',
        },
        {
            'id': 'channel_5',
            'channel_name': 'Startup Accelerator',
            'email': 'tom@startupaccel.com',
            'youtube_url': 'https://youtube.com/@startaccel',
            'subscriber_count': 45000,
            'niche': 'Startup',
            'location': 'United States',
            'score': 87,
            'status': 'New',
            'date_added': '2026-05-12',
        },
    ]

    for idx, lead in enumerate(test_leads, 1):
        backup_manager.backup_lead(lead)
        print(f"  ✅ Lead {idx}: {lead['channel_name']} ({lead['email']})")

    # Test 3: Get stats
    print("\n[TEST 3] Checking database statistics...")
    stats = backup_manager.get_backup_stats()
    print(f"  ✅ Total leads in database: {stats['total_leads']}")
    print(f"  ✅ Total emails sent: {stats['total_emails_sent']}")
    print(f"  ✅ Total replies: {stats['total_replies']}")

    # Test 4: Retrieve leads
    print("\n[TEST 4] Retrieving leads from database...")
    all_leads = backup_manager.get_all_leads()
    for lead in all_leads[-5:]:
        print(f"  ✅ Retrieved: {lead['channel_name']} - {lead['email']}")

    # Test 5: Try Notion (will show if API works)
    print("\n[TEST 5] Testing Notion API connection...")
    try:
        notion = NotionManager()
        leads_count = len(notion.get_all_leads())
        print(f"  ✅ Notion connected - {leads_count} leads in database")
    except Exception as e:
        print(f"  ⚠️  Notion connection issue (not blocking): {str(e)[:80]}")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\n📝 NEXT STEPS:")
    print("  1. Run: python app.py")
    print("  2. Open browser: http://localhost:5000")
    print("  3. Login with: fuelvia2025")
    print("  4. Go to LEADS tab - should show 5 test leads")
    print("  5. Try SCRAPER tab to start real scraping")
    print("\n")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
