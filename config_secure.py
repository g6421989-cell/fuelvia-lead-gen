# ============================================================
# SECURE CONFIG - Load from .env file (NOT from config.py)
# ============================================================

import os
from dotenv import load_dotenv
from error_logger import logger

# Load .env file
load_dotenv()

# ─── YOUTUBE API KEYS (8 keys - auto-rotate on quota exceeded) ───
YOUTUBE_APIS = [key for key in [
    os.getenv("YOUTUBE_API_KEY_1", ""),
    os.getenv("YOUTUBE_API_KEY_2", ""),
    os.getenv("YOUTUBE_API_KEY_3", ""),
    os.getenv("YOUTUBE_API_KEY_4", ""),
    os.getenv("YOUTUBE_API_KEY_5", ""),
    os.getenv("YOUTUBE_API_KEY_6", ""),
    os.getenv("YOUTUBE_API_KEY_7", ""),
    os.getenv("YOUTUBE_API_KEY_8", ""),
] if key]  # Only include keys that are actually set

# Validate YouTube keys
if not YOUTUBE_APIS:
    logger.log_error("❌ No YouTube API keys found in .env file")
else:
    print(f"  [OK] {len(YOUTUBE_APIS)} YouTube API key(s) loaded - rotation enabled")

CURRENT_API_INDEX = 0

# ─── NOTION API ───
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    logger.log_error("❌ Notion credentials missing in .env file")

# ─── CLAUDE API ───
ANTHROPIC_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-4-20250514")

if not ANTHROPIC_API_KEY:
    logger.log_error("❌ Claude API key missing in .env file")

# ─── OUTREACH EMAIL ACCOUNTS (3 accounts) ───
OUTREACH_ACCOUNTS = [
    {
        "email": os.getenv("OUTREACH_EMAIL_1", ""),
        "password": os.getenv("OUTREACH_PASSWORD_1", ""),
        "smtp_server": os.getenv("OUTREACH_SMTP_1", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("OUTREACH_PORT_1", "587")),
        "imap_server": "imap.gmail.com",
    },
    {
        "email": os.getenv("OUTREACH_EMAIL_2", ""),
        "password": os.getenv("OUTREACH_PASSWORD_2", ""),
        "smtp_server": os.getenv("OUTREACH_SMTP_2", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("OUTREACH_PORT_2", "587")),
        "imap_server": "imap.gmail.com",
    },
    {
        "email": os.getenv("OUTREACH_EMAIL_3", ""),
        "password": os.getenv("OUTREACH_PASSWORD_3", ""),
        "smtp_server": os.getenv("OUTREACH_SMTP_3", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("OUTREACH_PORT_3", "587")),
        "imap_server": "imap.gmail.com",
    },
]

CURRENT_OUTREACH_INDEX = 0

# ─── REPORTING EMAIL ACCOUNT ───
REPORTING_ACCOUNT = {
    "email": os.getenv("REPORTING_EMAIL", ""),
    "password": os.getenv("REPORTING_PASSWORD", ""),
    "smtp_server": os.getenv("REPORTING_SMTP", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("REPORTING_PORT", "587")),
    "imap_server": "imap.gmail.com",
}

if not REPORTING_ACCOUNT["email"]:
    logger.log_error("❌ Reporting email missing in .env file")

# ─── SYSTEM SETTINGS ───
EMAIL_ROTATION_DELAY = int(os.getenv("EMAIL_ROTATION_DELAY", "60"))
DAILY_REPORT_TIME = os.getenv("DAILY_REPORT_TIME", "17:00")
CALENDAR_LINK = os.getenv("CALENDAR_LINK", "")

# ─── COMPANY INFO ───
SENDER_NAME = os.getenv("SENDER_NAME", "Jashan A.")
SENDER_TITLE = os.getenv("SENDER_TITLE", "Founder")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Fuelvia")
INSTAGRAM = os.getenv("INSTAGRAM", "")

# ─── ERROR LOGGING ───
LOG_FILE = os.getenv("LOG_FILE", "logs/system.log")
ERROR_LOG_FILE = os.getenv("ERROR_LOG_FILE", "logs/errors.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
ALERT_ON_ERROR = os.getenv("ALERT_ON_ERROR", "true").lower() == "true"

# ─── DATABASE BACKUP ───
BACKUP_DATABASE_PATH = os.getenv("BACKUP_DATABASE_PATH", "backups/")
BACKUP_FREQUENCY = os.getenv("BACKUP_FREQUENCY", "daily")
KEEP_BACKUPS_DAYS = int(os.getenv("KEEP_BACKUPS_DAYS", "30"))

# ─── SYSTEM MODE ───
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ─── PRIVACY & COMPLIANCE ───
UNSUBSCRIBE_ENABLED = os.getenv("UNSUBSCRIBE_ENABLED", "true").lower() == "true"
PRIVACY_POLICY_URL = os.getenv("PRIVACY_POLICY_URL", "")
TERMS_URL = os.getenv("TERMS_URL", "")
GDPR_COMPLIANT = os.getenv("GDPR_COMPLIANT", "true").lower() == "true"

# ─── NICHE & SEARCH CONFIGURATION ───
NICHE_SEARCH_TERMS = {
    "Business Coach": [
        "business coach", "business coaching", "executive coach", "entrepreneur coach",
        "small business coach", "business growth coach", "leadership coach"
    ],
    "Marketing Expert": [
        "digital marketing", "marketing strategist", "marketing consultant", "growth marketing",
        "content marketing expert", "marketing coach", "performance marketing"
    ],
    "Agency Owner": [
        "marketing agency", "digital agency", "creative agency", "agency owner",
        "social media agency", "advertising agency", "branding agency"
    ],
    "SaaS Founder": [
        "SaaS founder", "software founder", "startup founder", "tech entrepreneur",
        "software as a service", "product founder", "B2B SaaS"
    ],
    "B2B Consultant": [
        "business consultant", "strategy consultant", "management consultant", "B2B consultant",
        "sales consultant", "operations consultant", "business advisor"
    ],
    "Real Estate Coach": [
        "real estate agent", "realtor", "real estate coach", "real estate investor",
        "real estate training", "real estate team leader", "real estate mentor"
    ],
    "Financial Advisor": [
        "financial advisor", "financial planner", "wealth management", "investment advisor",
        "financial coach", "retirement planning", "wealth advisor"
    ],
    "Course Creator": [
        "online course creator", "course creator", "online educator", "digital course",
        "online teaching", "info product creator", "membership site owner"
    ],
    "Entrepreneur": [
        "entrepreneur", "business owner", "startup founder", "small business owner",
        "online business", "ecommerce owner", "business builder"
    ],
    "E-Commerce Expert": [
        "ecommerce", "dropshipping", "shopify", "amazon fba", "online store owner",
        "ecommerce coach", "product seller", "print on demand"
    ],
    "Affiliate Marketer": [
        "affiliate marketing", "affiliate marketer", "passive income", "amazon affiliate",
        "affiliate network", "commission based", "affiliate program"
    ],
    "YouTube Creator": [
        "youtube channel", "content creator", "youtuber", "video creator",
        "youtube coaching", "channel growth", "video monetization"
    ],
    "Social Media Manager": [
        "social media manager", "social media marketer", "instagram expert", "tiktok creator",
        "social media agency", "community manager", "social media coach"
    ],
    "Email Marketing": [
        "email marketing", "email strategist", "email list", "email campaign",
        "email automation", "newsletter", "email coach"
    ],
    "SEO Specialist": [
        "SEO specialist", "search engine optimization", "SEO consultant", "SEO agency",
        "link building", "SEO expert", "ranking boost"
    ],
    "Sales Expert": [
        "sales coach", "sales consultant", "sales trainer", "sales expert",
        "closing techniques", "b2b sales", "sales funnel"
    ],
    "Customer Success": [
        "customer success", "customer retention", "customer experience", "customer service",
        "CS manager", "user onboarding", "customer development"
    ],
    "Product Manager": [
        "product manager", "product management", "product strategy", "product launch",
        "PM", "product development", "roadmap planning"
    ],
    "Dev/Tech": [
        "software developer", "web developer", "app developer", "programmer",
        "coding", "tech expert", "software engineer"
    ],
    "AI/Machine Learning": [
        "AI expert", "machine learning", "artificial intelligence", "AI tools",
        "chatgpt", "automation ai", "AI consulting"
    ],
    "Design Expert": [
        "graphic designer", "ux designer", "web designer", "ui designer",
        "branding", "design agency", "design consultant"
    ],
    "Fitness Coach": [
        "fitness coach", "personal trainer", "health coach", "nutrition coach",
        "gym owner", "fitness business", "wellness coach"
    ],
    "Online Education": [
        "online instructor", "online teacher", "edtech", "learning platform",
        "training program", "educational content", "skill courses"
    ],
}

NICHE_OPTIONS = list(NICHE_SEARCH_TERMS.keys()) + ["Custom"]

LOCATION_OPTIONS = {
    "Tier 1 English (USA+UK+CA+AU+NZ+IE)": ["USA", "UK", "Canada", "Australia", "New Zealand", "Ireland"],
    "North America (USA+CA+MX)": ["USA", "Canada", "Mexico"],
    "Europe (UK+DE+FR+NL+SE)": ["UK", "Germany", "France", "Netherlands", "Sweden"],
    "APAC (AU+NZ+SG+IN)": ["Australia", "New Zealand", "Singapore", "India"],
    "United States only": ["USA"],
    "United Kingdom only": ["UK"],
    "Canada only": ["Canada"],
    "Australia only": ["Australia"],
    "New Zealand only": ["New Zealand"],
    "Germany only": ["Germany"],
    "France only": ["France"],
    "India only": ["India"],
    "Singapore only": ["Singapore"],
    "Ireland only": ["Ireland"],
    "Netherlands only": ["Netherlands"],
    "Sweden only": ["Sweden"],
    "Global (no location filter)": [""],
}

SUBSCRIBER_RANGES = {
    "< 10K (Very Small)": (0, 10000),
    "10K - 25K (Small)": (10000, 25000),
    "25K - 50K (Small-Mid)": (25000, 50000),
    "< 50K (All Under 50K)": (0, 50000),
    "50K - 100K (Mid)": (50000, 100000),
    "< 1 Lakh (Under 100K)": (0, 100000),
    "1K - 5K": (1000, 5000),
    "5K - 10K": (5000, 10000),
    "10K - 20K": (10000, 20000),
    "20K - 50K": (20000, 50000),
    "50K - 100K": (50000, 100000),
    "100K - 500K (Large)": (100000, 500000),
    "500K+ (Very Large)": (500000, None),
}


def get_reporting_email_config():
    """Get reporting email configuration"""
    return REPORTING_ACCOUNT


def get_youtube_api_keys():
    """Get all YouTube API keys"""
    return [key for key in YOUTUBE_APIS if key]


def get_outreach_accounts():
    """Get all outreach email accounts"""
    return [acc for acc in OUTREACH_ACCOUNTS if acc["email"]]


def validate_config():
    """Validate all required configuration"""
    errors = []

    if not any(YOUTUBE_APIS):
        errors.append("No YouTube API keys configured")

    if not NOTION_API_KEY:
        errors.append("Notion API key missing")

    if not ANTHROPIC_API_KEY:
        errors.append("Claude API key missing")

    if not any(acc["email"] for acc in OUTREACH_ACCOUNTS):
        errors.append("No outreach email accounts configured")

    if not REPORTING_ACCOUNT["email"]:
        errors.append("Reporting email account missing")

    if errors:
        logger.log_critical("Configuration validation failed:")
        for error in errors:
            logger.log_error(f"  - {error}")
        return False

    logger.log_success("✅ Configuration validated successfully")
    return True


if __name__ == "__main__":
    validate_config()
