# ============================================================
# FUELVIA LEAD GENERATION SYSTEM - CONFIG v3
# ============================================================
#
# SUSTAINABILITY MATHS (60 leads/day target, 7-9 months):
#   22 niches × 13 keywords × 8 locations = 2,288 search combos
#   Dual-source (channel + video) doubles the channel pool per combo
#   Effective unique pool: ~50,000-80,000 qualifying channels
#   Pool replenishes daily as new creators cross subscriber thresholds
#   → System can sustain 60 leads/day for 12+ months
#
# DAILY ROTATION GUIDE (to maximise freshness):
#   Mon: Business coaching niches  + USA/UK
#   Tue: Marketing/Agency niches   + Canada/Australia
#   Wed: Finance/Real estate niches + Global
#   Thu: Creator/Course niches     + USA/UK
#   Fri: Tech/SaaS niches          + Canada/Australia
#   Sat: Health/Life coaching      + Global
#   Sun: Sales/Consulting niches   + USA/UK
#   → Rotate through 8 subscriber ranges weekly for deepest coverage
#
# API KEYS — HOW TO GET MORE:
#   1. Go to console.cloud.google.com
#   2. Create a new project (1 per Gmail account)
#   3. Enable "YouTube Data API v3"
#   4. Create credentials → API Key
#   5. Add key as YOUTUBE_API_5, YOUTUBE_API_6, etc.
#   Each key = 10,000 units/day. 60 leads needs ~3,000 units.
#   You currently have 4 keys (40,000 units). For sustained 60/day,
#   add 4 more keys = 8 total = 80,000 units = plenty of headroom.
# ============================================================

import os

# ── YouTube API Keys (add more for higher daily volume) ───────────────
# HOW TO ADD MORE: see notes above. Each extra key = 10k units/day.
YOUTUBE_APIS = [k for k in [
    os.getenv("YOUTUBE_API_1"),
    os.getenv("YOUTUBE_API_2"),
    os.getenv("YOUTUBE_API_3"),
    os.getenv("YOUTUBE_API_4"),
    os.getenv("YOUTUBE_API_5"),   # add these in Render env vars
    os.getenv("YOUTUBE_API_6"),   # when you get more API keys
    os.getenv("YOUTUBE_API_7"),
    os.getenv("YOUTUBE_API_8"),
] if k]  # auto-filters out empty/unset keys

CURRENT_API_INDEX = 0

# ── Notion API ────────────────────────────────────────────────────────
NOTION_API_KEY      = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID  = os.getenv("NOTION_DATABASE_ID")

# ── OUTREACH EMAIL ACCOUNTS ───────────────────────────────────────────
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
CURRENT_OUTREACH_INDEX = 0

# ── Reporting account ─────────────────────────────────────────────────
REPORTING_ACCOUNT = {
    "email": "Fuelviaa01@gmail.com",
    "password": "hwwe yhel nmns ofwo",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_server": "imap.gmail.com",
}

# ── System settings ───────────────────────────────────────────────────
EMAIL_ROTATION_DELAY = 120   # 2 min gap between sends (domain reputation)
DAILY_REPORT_TIME    = "17:00"
CALENDAR_LINK        = "https://calendly.com/fuelvia-co/30min?month=2026-05"
SENDER_NAME          = "Jashan A."
SENDER_TITLE         = "Founder"
COMPANY_NAME         = "Fuelvia"
INSTAGRAM            = "https://instagram.com/fuelviaa"

# ── Claude API ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL      = "anthropic/claude-sonnet-4-20250514"


# ════════════════════════════════════════════════════════════════════
# NICHE SEARCH TERMS — 22 niches, 12-14 keywords each
# ════════════════════════════════════════════════════════════════════
# Why 22 niches?  Each is a separate creator category with a distinct
# pool of channels.  Using all 22 in rotation across 8 locations gives
# 2,200+ keyword-location combos — enough for 12+ months of fresh
# leads without repeating the same channels (blacklist prevents that).
#
# ROTATION TIP: Don't scrape the same niche two days in a row.
# Spread across different category groups each day.
# ════════════════════════════════════════════════════════════════════

NICHE_SEARCH_TERMS = {

    # ── GROUP 1: Business & Coaching ─────────────────────────────
    "Business Coach": [
        "business coach",
        "business coaching tips",
        "executive coach",
        "entrepreneur coach",
        "small business coach",
        "business growth coach",
        "leadership coach",
        "business success coach",
        "CEO coach",
        "entrepreneurship coaching",
        "business mindset coach",
        "scaling a business",
    ],

    "Life Coach": [
        "life coach",
        "life coaching tips",
        "mindset coach",
        "personal development coach",
        "transformation coach",
        "success coach",
        "confidence coach",
        "self improvement coach",
        "goal setting coach",
        "high performance coach",
        "abundance mindset",
        "personal growth tips",
    ],

    "Career Coach": [
        "career coach",
        "career coaching",
        "job search coach",
        "resume coach",
        "interview coach",
        "career change advice",
        "career development tips",
        "professional development coach",
        "LinkedIn career tips",
        "job interview tips",
        "career growth strategies",
        "salary negotiation coach",
    ],

    "Relationship Coach": [
        "relationship coach",
        "dating coach",
        "marriage coach",
        "couples coach",
        "love coach",
        "dating advice",
        "relationship advice",
        "communication in relationships",
        "healthy relationship tips",
        "breakup coach",
        "attraction coach",
        "social skills coach",
    ],

    # ── GROUP 2: Marketing & Online Business ──────────────────────
    "Marketing Expert": [
        "digital marketing",
        "marketing strategist",
        "marketing consultant",
        "growth marketing tips",
        "content marketing",
        "marketing coach",
        "performance marketing",
        "paid ads expert",
        "Facebook ads tips",
        "Google ads tutorial",
        "online marketing strategy",
        "marketing for small business",
    ],

    "Agency Owner": [
        "marketing agency owner",
        "digital agency",
        "agency owner tips",
        "social media agency",
        "advertising agency",
        "branding agency",
        "agency growth",
        "SMMA tips",
        "social media marketing agency",
        "running a marketing agency",
        "agency business model",
        "client acquisition agency",
    ],

    "Social Media Expert": [
        "social media tips",
        "social media marketing tips",
        "Instagram growth tips",
        "TikTok growth tips",
        "YouTube growth tips",
        "social media strategy",
        "content creation tips",
        "social media manager tips",
        "grow social media following",
        "personal branding tips",
        "building an audience online",
        "organic growth tips",
    ],

    "LinkedIn Expert": [
        "LinkedIn tips",
        "LinkedIn growth",
        "LinkedIn marketing",
        "LinkedIn personal branding",
        "LinkedIn content strategy",
        "LinkedIn lead generation",
        "B2B LinkedIn tips",
        "LinkedIn for business",
        "LinkedIn coach",
        "professional branding tips",
        "thought leadership LinkedIn",
        "LinkedIn profile tips",
    ],

    # ── GROUP 3: Sales & Consulting ───────────────────────────────
    "Sales Expert": [
        "sales coach",
        "sales training",
        "closing sales tips",
        "sales strategies",
        "cold calling tips",
        "sales mindset",
        "B2B sales tips",
        "high ticket sales",
        "sales techniques",
        "objection handling sales",
        "sales funnel tips",
        "commission sales tips",
    ],

    "B2B Consultant": [
        "business consultant",
        "strategy consultant",
        "management consultant",
        "B2B consultant",
        "operations consultant",
        "business advisor",
        "business strategy tips",
        "consulting tips",
        "fractional CMO",
        "fractional CFO tips",
        "business systems",
        "process improvement consultant",
    ],

    # ── GROUP 4: Finance & Investment ─────────────────────────────
    "Financial Advisor": [
        "financial advisor",
        "financial planner tips",
        "wealth management tips",
        "investment advisor",
        "financial coach",
        "retirement planning tips",
        "wealth building tips",
        "personal finance tips",
        "money management tips",
        "financial freedom",
        "passive income strategies",
        "budgeting tips",
    ],

    "Investing & Stocks": [
        "stock market tips",
        "investing for beginners",
        "stock market investing",
        "dividend investing",
        "index fund investing",
        "stock market education",
        "value investing",
        "growth investing",
        "ETF investing tips",
        "investment strategies",
        "portfolio management",
        "options trading tips",
    ],

    # ── GROUP 5: Real Estate ──────────────────────────────────────
    "Real Estate Coach": [
        "real estate agent tips",
        "realtor tips",
        "real estate coaching",
        "real estate investor",
        "real estate training",
        "real estate team leader",
        "real estate mentor",
        "how to become a realtor",
        "real estate business tips",
        "real estate lead generation",
        "listing agent tips",
        "buyer agent tips",
    ],

    "Real Estate Investor": [
        "real estate investing",
        "rental property investing",
        "house flipping tips",
        "BRRRR strategy real estate",
        "short term rental tips",
        "Airbnb host tips",
        "commercial real estate",
        "multifamily investing",
        "real estate syndication",
        "passive real estate",
        "property investing tips",
        "landlord tips",
    ],

    # ── GROUP 6: Online Creators ──────────────────────────────────
    "Course Creator": [
        "online course creator",
        "course creation tips",
        "how to create online course",
        "digital course tips",
        "online coaching business",
        "membership site tips",
        "info product creator",
        "online education business",
        "teach online tips",
        "course launch tips",
        "knowledge business",
        "expert business tips",
    ],

    "Podcaster": [
        "podcast tips",
        "podcasting for beginners",
        "how to start a podcast",
        "podcast growth tips",
        "podcast host tips",
        "podcast monetization",
        "business podcast tips",
        "podcast marketing",
        "podcast interview tips",
        "podcast production tips",
        "podcast strategy",
        "growing a podcast audience",
    ],

    # ── GROUP 7: E-commerce ───────────────────────────────────────
    "E-commerce / Dropshipping": [
        "ecommerce tips",
        "dropshipping tips",
        "Shopify tips",
        "online store tips",
        "ecommerce business tips",
        "dropshipping for beginners",
        "Shopify dropshipping",
        "ecommerce marketing",
        "product research dropshipping",
        "ecommerce store setup",
        "online selling tips",
        "ecommerce scaling tips",
    ],

    "Amazon FBA": [
        "Amazon FBA tips",
        "Amazon seller tips",
        "Amazon FBA for beginners",
        "private label Amazon",
        "Amazon business tips",
        "Amazon product research",
        "Amazon marketing tips",
        "Amazon PPC tips",
        "selling on Amazon tips",
        "Amazon brand building",
        "Amazon automation tips",
        "FBA seller tips",
    ],

    # ── GROUP 8: Tech & SaaS ──────────────────────────────────────
    "SaaS Founder": [
        "SaaS founder tips",
        "software startup tips",
        "SaaS growth tips",
        "startup founder advice",
        "B2B SaaS tips",
        "SaaS marketing tips",
        "product-led growth",
        "SaaS business tips",
        "startup growth hacks",
        "building SaaS product",
        "SaaS pricing tips",
        "inbound marketing SaaS",
    ],

    # ── GROUP 9: Health & Fitness ─────────────────────────────────
    "Fitness Coach": [
        "fitness coach tips",
        "personal trainer tips",
        "online fitness coach",
        "fitness business tips",
        "workout tips for coaches",
        "nutrition coach",
        "weight loss coach",
        "strength training tips",
        "fitness entrepreneur",
        "gym owner tips",
        "fitness influencer tips",
        "health coach tips",
    ],

    # ── GROUP 10: Mindset & Motivation ────────────────────────────
    "Mindset & Motivation": [
        "mindset tips",
        "motivation tips",
        "success mindset",
        "discipline tips",
        "morning routine tips",
        "productivity tips",
        "habits for success",
        "self discipline tips",
        "mental toughness tips",
        "growth mindset tips",
        "law of attraction tips",
        "manifestation tips",
    ],

    # ── GROUP 11: Legal & Professional Services ────────────────────
    "Attorney / Legal": [
        "lawyer tips",
        "attorney advice",
        "legal tips for business",
        "business law tips",
        "contract tips for entrepreneurs",
        "startup legal tips",
        "intellectual property tips",
        "trademark tips",
        "real estate law tips",
        "family law tips",
        "legal advice for small business",
        "law firm marketing",
    ],
}


# ── Display list for dashboard dropdown ──────────────────────────────
NICHE_OPTIONS = list(NICHE_SEARCH_TERMS.keys()) + ["Custom"]


# ════════════════════════════════════════════════════════════════════
# LOCATION OPTIONS — 11 options across all English-speaking markets
# ════════════════════════════════════════════════════════════════════
# ROTATION TIP: Different locations surface different creators.
# Using "All English" one day, then "USA only" the next gives you
# fresh channels because the search ranking algorithm differs.
# ════════════════════════════════════════════════════════════════════

LOCATION_OPTIONS = {
    "🌍 All English (USA+UK+CA+AU+NZ+ZA)": ["USA", "UK", "Canada", "Australia", "New Zealand", "South Africa"],
    "🇺🇸 United States only":               ["USA"],
    "🇬🇧 United Kingdom only":               ["UK"],
    "🇨🇦 Canada only":                       ["Canada"],
    "🇦🇺 Australia only":                    ["Australia"],
    "🇳🇿 New Zealand only":                  ["New Zealand"],
    "🇿🇦 South Africa only":                 ["South Africa"],
    "🌎 Global (no location filter)":        [""],
    "🇺🇸🇨🇦 North America (USA+Canada)":    ["USA", "Canada"],
    "🇬🇧🇮🇪 UK + Ireland":                  ["UK", "Ireland"],
    "🌏 Asia-Pacific (AU+NZ)":              ["Australia", "New Zealand"],
}


# ════════════════════════════════════════════════════════════════════
# SUBSCRIBER RANGES
# ════════════════════════════════════════════════════════════════════
# ROTATION TIP: Rotate ranges weekly. Each range is a completely
# different set of channels. A creator with 3K subs won't appear
# in a 10K-20K search, and vice versa.
#
# WEEK 1: 1K-5K   (micro creators — highest reply rates)
# WEEK 2: 5K-10K  (growing creators)
# WEEK 3: 10K-20K (established small creators)
# WEEK 4: 20K-50K (mid-tier — fewer leads but higher value)
# ════════════════════════════════════════════════════════════════════

SUBSCRIBER_RANGES = {
    "1,000 - 20,000 (RECOMMENDED)":  (1_000,   20_000),
    "1,000 - 5,000 (Micro)":         (1_000,    5_000),
    "5,000 - 10,000 (Growing)":      (5_000,   10_000),
    "10,000 - 20,000 (Established)": (10_000,  20_000),
    "20,000 - 50,000 (Mid-tier)":    (20_000,  50_000),
    "50,000 - 100,000 (Large)":      (50_000, 100_000),
    "1,000 - 10,000 (Small)":        (1_000,   10_000),
    "10,000 - 30,000":               (10_000,  30_000),
    "500 - 2,000 (Nano)":            (500,      2_000),
    "100,000+ (Macro)":              (100_000,   None),
}
