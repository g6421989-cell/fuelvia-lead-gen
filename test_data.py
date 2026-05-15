"""
TEST DATA INSERTION - Populate Notion with sample leads
USAGE: python test_data.py
No API credits consumed - direct Notion insertion only
"""

from datetime import datetime, timedelta
from notion_manager import NotionManager

# Sample test leads
TEST_LEADS = [
    {
        "channel_name": "John's Business Coaching Hub",
        "email": "john@businesscoaching.com",
        "youtube_url": "https://youtube.com/channel/UCjohn123business",
        "subscriber_count": 12500,
        "niche": "Business Coach",
        "location": "Global",
        "score": 8,
        "score_reason": "Strong B2B fit, consistent uploads, engaged audience"
    },
    {
        "channel_name": "Sarah's Agency Growth Secrets",
        "email": "sarah@agencygrowth.com",
        "youtube_url": "https://youtube.com/channel/UCsarah456agency",
        "subscriber_count": 8750,
        "niche": "Agency Owner",
        "location": "United States",
        "score": 7,
        "score_reason": "High-quality content, target audience match"
    },
    {
        "channel_name": "Mike's SaaS Scaling Stories",
        "email": "mike@saasscaling.com",
        "youtube_url": "https://youtube.com/channel/UCmike789saas",
        "subscriber_count": 15200,
        "niche": "SaaS Founder",
        "location": "United Kingdom",
        "score": 9,
        "score_reason": "Excellent content, perfect target market, highly relevant"
    },
    {
        "channel_name": "Lisa's Consultant Insights",
        "email": "lisa@consultantinsights.com",
        "youtube_url": "https://youtube.com/channel/UClisa101consultant",
        "subscriber_count": 11000,
        "niche": "B2B Consultant",
        "location": "Canada",
        "score": 6,
        "score_reason": "Good fit, moderate engagement, relevant niche"
    },
    {
        "channel_name": "David's Entrepreneur Edge",
        "email": "david@entrepreneuredge.com",
        "youtube_url": "https://youtube.com/channel/UCdavid202entrepreneur",
        "subscriber_count": 13400,
        "niche": "Entrepreneur",
        "location": "Australia",
        "score": 8,
        "score_reason": "Strong audience, consistent posting, high-quality production"
    }
]

def insert_test_data():
    """Insert test leads into Notion"""
    notion = NotionManager()

    print("\n" + "=" * 60)
    print("  INSERTING TEST DATA INTO NOTION")
    print("=" * 60 + "\n")

    for i, lead in enumerate(TEST_LEADS, 1):
        print(f"  📝 Adding lead {i}/5: {lead['channel_name']}...")
        try:
            notion.create_lead(lead)
            print(f"  ✅ Added to Notion\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")

    # Get stats
    all_leads = notion.get_all_leads()
    print("=" * 60)
    print(f"✅ TEST DATA COMPLETE!")
    print(f"   Total leads in Notion: {len(all_leads)}")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("   1. Check your Notion database - should have 5 test leads")
    print("   2. Run: python followup.py (to test follow-ups)")
    print("   3. Run: python generate.py (for real leads with API)")
    print("\n")

if __name__ == "__main__":
    insert_test_data()
