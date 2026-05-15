# ============================================================
# FUELVIA LEAD GENERATION SYSTEM - CONFIG (NOTION + API ROTATION)
# ============================================================

import os

# YouTube APIs (4 total - rotates when quota exceeded)
YOUTUBE_APIS = [
    os.getenv("YOUTUBE_API_1"),
    os.getenv("YOUTUBE_API_2"),
    os.getenv("YOUTUBE_API_3"),
    os.getenv("YOUTUBE_API_4")
]
CURRENT_API_INDEX = 0  # Auto-rotates on quota error

# Notion API
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# OUTREACH EMAIL ACCOUNTS (3 total - for sending to leads)
OUTREACH_ACCOUNTS = [
    {
        "email": "fuelvia.co@gmail.com",
        "password": "bafv dvme pduz nwgi",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_server": "imap.gmail.com",
    },
    {
        "email": "fuelviasubscriptions@gmail.com",
        "password": "qzct ffev dsrt ijpg",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_server": "imap.gmail.com",
    },
    {
        "email": "fuelvia.co01@gmail.com",
        "password": "tnqy neym fucb irto",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_server": "imap.gmail.com",
    },
]
CURRENT_OUTREACH_INDEX = 0  # Rotates through accounts

# REPORTING EMAIL ACCOUNT (Isolated - for reports only)
REPORTING_ACCOUNT = {
    "email": "Fuelviaa01@gmail.com",
    "password": "hwwe yhel nmns ofwo",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_server": "imap.gmail.com",
}

# System settings
EMAIL_ROTATION_DELAY = 120  # 2 minutes between emails — safe zone for 3-account rotation
DAILY_REPORT_TIME = "17:00"

# Calendly link (UPDATED)
CALENDAR_LINK = "https://calendly.com/fuelvia-co/30min?month=2026-05"

# Company info (UPDATED for Founders & Coaches)
SENDER_NAME = "Jashan A."
SENDER_TITLE = "Founder"
COMPANY_NAME = "Fuelvia"
INSTAGRAM = "https://instagram.com/fuelviaa"

# MULTI-KEYWORD SEARCH MAPPING (5-7 variations per niche)
# Each niche gets multiple search terms for better coverage
NICHE_SEARCH_TERMS = {
    "Business Coach": [
        "business coach",
        "business coaching",
        "executive coach",
        "entrepreneur coach",
        "small business coach",
        "business growth coach",
        "leadership coach"
    ],

    "Marketing Expert": [
        "digital marketing",
        "marketing strategist",
        "marketing consultant",
        "growth marketing",
        "content marketing expert",
        "marketing coach",
        "performance marketing"
    ],

    "Agency Owner": [
        "marketing agency",
        "digital agency",
        "creative agency",
        "agency owner",
        "social media agency",
        "advertising agency",
        "branding agency"
    ],

    "SaaS Founder": [
        "SaaS founder",
        "software founder",
        "startup founder",
        "tech entrepreneur",
        "software as a service",
        "product founder",
        "B2B SaaS"
    ],

    "B2B Consultant": [
        "business consultant",
        "strategy consultant",
        "management consultant",
        "B2B consultant",
        "sales consultant",
        "operations consultant",
        "business advisor"
    ],

    "Real Estate Coach": [
        "real estate agent",
        "realtor",
        "real estate coach",
        "real estate investor",
        "real estate training",
        "real estate team leader",
        "real estate mentor"
    ],

    "Financial Advisor": [
        "financial advisor",
        "financial planner",
        "wealth management",
        "investment advisor",
        "financial coach",
        "retirement planning",
        "wealth advisor"
    ],

    "Course Creator": [
        "online course creator",
        "course creator",
        "online educator",
        "digital course",
        "online teaching",
        "info product creator",
        "membership site owner"
    ],

    "Entrepreneur": [
        "entrepreneur",
        "business owner",
        "startup founder",
        "small business owner",
        "online business",
        "ecommerce owner",
        "business builder"
    ],
}

# For menu display
NICHE_OPTIONS = list(NICHE_SEARCH_TERMS.keys()) + ["Custom"]

# Location options (now returns list of location terms)
# English-speaking locations paired together for broader reach
LOCATION_OPTIONS = {
    "🌍 English-speaking (USA+UK+CA+AU)": ["USA", "UK", "Canada", "Australia"],
    "🇺🇸 United States only": ["USA"],
    "🇬🇧 United Kingdom only": ["UK"],
    "🇨🇦 Canada only": ["Canada"],
    "🇦🇺 Australia only": ["Australia"],
    "🌎 Global (no location filter)": [""],
}

# EXPANDED Subscriber ranges (better coverage)
SUBSCRIBER_RANGES = {
    "1,000 - 20,000 (RECOMMENDED)": (1000, 20000),
    "20,000 - 50,000": (20000, 50000),
    "50,000 - 100,000": (50000, 100000),
    "1,000 - 5,000 (Small)": (1000, 5000),
    "5,000 - 10,000": (5000, 10000),
    "10,000 - 15,000": (10000, 15000),
    "15,000 - 20,000": (15000, 20000),
    "100,000+ (Large)": (100000, None),
}

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "anthropic/claude-sonnet-4-20250514"
