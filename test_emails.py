# ============================================================
# TEST SCRIPT — Generate 3 sample emails to verify variation
# ============================================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from claude_helpers import write_personalized_initial_email

FAKE_LEADS = [
    {
        "channel_data": {
            "channel_name": "SystemsWithMike",
            "niche": "Business Automation",
            "subscriber_count": 8200,
            "days_since_upload": 12,
        },
        "videos_data": [
            {"title": "How I Automated My Entire Client Onboarding in 3 Hours"},
            {"title": "The Zapier Workflow That Saved Me 10 Hours a Week"},
            {"title": "Why Most Business Owners Build Broken Systems"},
            {"title": "Notion + Make.com: My Full Business OS Walkthrough"},
            {"title": "Stop Using Spreadsheets — Do This Instead"},
        ],
    },
    {
        "channel_data": {
            "channel_name": "MindsetWithKira",
            "niche": "Life Coaching",
            "subscriber_count": 2200,
            "days_since_upload": 5,
        },
        "videos_data": [
            {"title": "Why You Keep Self-Sabotaging (And How to Stop)"},
            {"title": "Morning Routine That Changed My Mental Health"},
            {"title": "The Identity Shift No One Talks About"},
            {"title": "Stop Waiting for Motivation — Do This Instead"},
            {"title": "How I Went From Burned Out to Thriving in 60 Days"},
        ],
    },
    {
        "channel_data": {
            "channel_name": "LearnWithTariq",
            "niche": "Online Education",
            "subscriber_count": 18500,
            "days_since_upload": 8,
        },
        "videos_data": [
            {"title": "Full Python Crash Course for Beginners — 4 Hours"},
            {"title": "How I Made $12K Selling My First Online Course"},
            {"title": "My Exact Course Launch Checklist (Free Template)"},
            {"title": "Why 90% of Online Courses Fail (And Mine Didn't)"},
            {"title": "Notion Course Dashboard Setup — Full Tutorial"},
        ],
    },
]

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  FUELVIA - 3 TEST EMAILS (Anti-Template v3)")
    print("="*60)

    for i, lead in enumerate(FAKE_LEADS, 1):
        print(f"\n{'-'*60}")
        print(f"  LEAD {i}: {lead['channel_data']['channel_name']}")
        print(f"  Niche: {lead['channel_data']['niche']}  |  Subs: {lead['channel_data']['subscriber_count']:,}")
        print(f"{'-'*60}")

        subject, body = write_personalized_initial_email(
            lead["channel_data"],
            lead["videos_data"],
        )

        print(f"SUBJECT: {subject}\n")
        print(body)

    print(f"\n{'='*60}")
    print("  Done - 3 emails generated.")
    print("="*60 + "\n")
