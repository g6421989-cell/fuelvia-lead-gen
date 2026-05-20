# ============================================================
# FUELVIA LEAD GENERATION SYSTEM - CONFIG v4
# ============================================================
#
# WHO FUELVIA SERVES:
#   Coaches, consultants, and experts who use YouTube to attract
#   clients for their business. They post regularly (authority
#   building), have income from their business (can pay $235-$489/mo),
#   and need professional video editing to look credible.
#
# WHO TO AVOID:
#   - Amazon/e-commerce sellers (product-focused, not personal brand)
#   - Faceless finance/investing channels (no personal brand)
#   - Entertainment/gaming (no business buying video editing)
#   - Attorneys (rarely post videos, compliance-heavy)
#
# PERFECT LEAD PROFILE:
#   - Posts YouTube videos to attract coaching/consulting clients
#   - 1K-20K subscribers (growing, needs help scaling content)
#   - Has income from their business (coach, consultant, trainer)
#   - Posts at least once every 2 weeks (active)
#   - Has an email in their description (reachable)
#
# ════════════════════════════════════════════════════════════════
# SUSTAINABILITY MATHS (60 leads/day, 7-9 months):
#   16 niches × 14 keywords × 7 locations = 1,568 combos
#   Dual-source discovery (channel + video) = ~3x channel pool
#   publishedAfter filter surfaces new channels daily
#   Total accessible pool: ~60,000-100,000 qualifying channels
#   Pool replenishes as new creators cross the subscriber threshold
#   → System sustains 60 leads/day for 12+ months with rotation
#
# DAILY ROTATION GUIDE:
#   Mon:  Business + Life coaching    | USA
#   Tue:  Marketing + Agency          | UK + Canada
#   Wed:  Fitness + Health coaching   | Australia + NZ
#   Thu:  Course + Career coaching    | Global
#   Fri:  Real Estate + Finance       | USA + UK
#   Sat:  Sales + Mindset             | Canada + South Africa
#   Sun:  Personal Brand + Social     | All English-speaking
#
#   Subscriber range rotation (change weekly):
#   Week 1: 1K-5K (micro creators — highest reply rates)
#   Week 2: 5K-10K (growing creators)
#   Week 3: 10K-20K (established small creators)
#   Week 4: 20K-50K (mid-tier — fewer leads, higher value)
#
# HOW TO ADD MORE YOUTUBE API KEYS:
#   1. console.cloud.google.com → New Project
#   2. Enable "YouTube Data API v3"
#   3. Credentials → API Key
#   4. Add as YOUTUBE_API_5, YOUTUBE_API_6... in Render env vars
#   Each key = 10,000 units/day. 60 leads ≈ 3,000-5,000 units.
#   Current 4 keys = 40,000 units. Add 4 more = 80,000 = headroom.
# ============================================================

import os
from dotenv import load_dotenv
load_dotenv()   # loads .env file from project root

# ── YouTube API Keys ──────────────────────────────────────────────────
# Supports both naming conventions: YOUTUBE_API_KEY_1 (.env style)
# and YOUTUBE_API_1 (Render env var style). Auto-filters empty/unset.
YOUTUBE_APIS = [k for k in [
    os.getenv("YOUTUBE_API_KEY_1") or os.getenv("YOUTUBE_API_1"),
    os.getenv("YOUTUBE_API_KEY_2") or os.getenv("YOUTUBE_API_2"),
    os.getenv("YOUTUBE_API_KEY_3") or os.getenv("YOUTUBE_API_3"),
    os.getenv("YOUTUBE_API_KEY_4") or os.getenv("YOUTUBE_API_4"),
    os.getenv("YOUTUBE_API_KEY_5") or os.getenv("YOUTUBE_API_5"),
    os.getenv("YOUTUBE_API_KEY_6") or os.getenv("YOUTUBE_API_6"),
    os.getenv("YOUTUBE_API_KEY_7") or os.getenv("YOUTUBE_API_7"),
    os.getenv("YOUTUBE_API_KEY_8") or os.getenv("YOUTUBE_API_8"),
] if k]

CURRENT_API_INDEX = 0

# ── Notion ────────────────────────────────────────────────────────────
NOTION_API_KEY     = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# ── Email accounts ────────────────────────────────────────────────────
OUTREACH_ACCOUNTS = [
    {
        "email":       "fuelvia.co@gmail.com",
        "password":    "bafv dvme pduz nwgi",
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        "imap_server": "imap.gmail.com",
    },
    {
        "email":       "fuelviasubscriptions@gmail.com",
        "password":    "qzct ffev dsrt ijpg",
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        "imap_server": "imap.gmail.com",
    },
    {
        "email":       "fuelvia.co01@gmail.com",
        "password":    "tnqy neym fucb irto",
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        "imap_server": "imap.gmail.com",
    },
]
CURRENT_OUTREACH_INDEX = 0

REPORTING_ACCOUNT = {
    "email":       "Fuelviaa01@gmail.com",
    "password":    "hwwe yhel nmns ofwo",
    "smtp_server": "smtp.gmail.com",
    "smtp_port":   587,
    "imap_server": "imap.gmail.com",
}

# ── System settings ───────────────────────────────────────────────────
EMAIL_ROTATION_DELAY = 600  # 10 minutes between emails
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
# NICHE SEARCH TERMS — 16 niches, 14 keywords each
# ════════════════════════════════════════════════════════════════════
#
# Every niche here = someone who:
#   (a) builds a personal brand on YouTube
#   (b) uses videos to attract paying clients
#   (c) has budget for video editing ($235-$489/month)
#
# Keywords are designed to find people POSTING content on YouTube,
# not just people who exist in that industry. We want active creators.
# ════════════════════════════════════════════════════════════════════

NICHE_SEARCH_TERMS = {

    # ── TIER 1: Highest-value targets (business buyers with budget) ──

    "Business Coach": [
        "business coach YouTube",
        "business coaching tips",
        "executive coach YouTube",
        "entrepreneur coach",
        "small business coach tips",
        "business growth coach",
        "CEO coach YouTube",
        "scaling a business tips",
        "business success tips YouTube",
        "business mentorship YouTube",
        "entrepreneurship coach",
        "business strategy tips YouTube",
        "startup coaching tips",
        "founder coach YouTube",
    ],

    "Marketing Expert": [
        "digital marketing tips YouTube",
        "marketing coach YouTube",
        "marketing consultant tips",
        "content marketing tips",
        "marketing strategy YouTube",
        "social media marketing tips",
        "paid ads tips YouTube",
        "Facebook ads tips",
        "Google ads tutorial YouTube",
        "marketing for coaches",
        "online marketing tips",
        "personal brand marketing",
        "marketing agency tips YouTube",
        "growth marketing tips",
    ],

    "Sales Expert": [
        "sales coach YouTube",
        "sales tips YouTube",
        "closing sales tips",
        "high ticket sales tips",
        "sales training YouTube",
        "cold outreach tips YouTube",
        "sales mindset YouTube",
        "B2B sales tips",
        "objection handling sales",
        "sales call tips YouTube",
        "appointment setting tips",
        "discovery call tips",
        "sales funnel tips",
        "commission sales tips YouTube",
    ],

    "Agency Owner": [
        "marketing agency owner tips",
        "agency owner YouTube",
        "SMMA tips YouTube",
        "social media marketing agency tips",
        "agency growth tips",
        "client acquisition agency",
        "running a marketing agency",
        "digital agency tips YouTube",
        "video marketing agency",
        "creative agency tips",
        "branding agency YouTube",
        "agency business model tips",
        "freelance to agency YouTube",
        "agency scaling tips",
    ],

    # ── TIER 2: High-fit coaching & authority builders ───────────────

    "Life Coach": [
        "life coach YouTube",
        "life coaching tips",
        "mindset coach YouTube",
        "personal development YouTube",
        "transformation coach tips",
        "success coach YouTube",
        "confidence coach YouTube",
        "self improvement coach",
        "goal setting coach tips",
        "high performance coach YouTube",
        "life coach content creator",
        "personal growth YouTube",
        "mindset tips YouTube",
        "life coaching business tips",
    ],

    "Fitness Coach": [
        "fitness coach YouTube",
        "online fitness coach tips",
        "personal trainer YouTube",
        "fitness business tips YouTube",
        "online personal trainer tips",
        "nutrition coach YouTube",
        "weight loss coach YouTube",
        "strength training coach tips",
        "fitness entrepreneur YouTube",
        "gym owner tips YouTube",
        "health coach YouTube",
        "fitness influencer tips",
        "workout tips for coaches",
        "body transformation coach",
    ],

    "Real Estate Coach": [
        "real estate coach YouTube",
        "real estate agent tips YouTube",
        "realtor tips YouTube",
        "real estate investor tips YouTube",
        "real estate training YouTube",
        "real estate mentor tips",
        "real estate team leader tips",
        "how to become a realtor YouTube",
        "real estate business tips",
        "real estate lead generation tips",
        "real estate content creator",
        "property investing tips YouTube",
        "real estate YouTube channel",
        "real estate coaching business",
    ],

    "Financial Advisor": [
        "financial advisor YouTube",
        "financial coach YouTube",
        "financial educator YouTube",
        "personal finance tips YouTube",
        "financial planning tips YouTube",
        "money coach tips YouTube",
        "wealth building tips YouTube",
        "financial literacy YouTube",
        "money management tips YouTube",
        "financial freedom tips YouTube",
        "budgeting tips YouTube",
        "debt free journey YouTube",
        "financial independence tips",
        "money mindset coach YouTube",
    ],

    "Career Coach": [
        "career coach YouTube",
        "career coaching tips YouTube",
        "job search tips YouTube",
        "resume tips YouTube",
        "interview tips YouTube",
        "career change tips YouTube",
        "career development YouTube",
        "professional development coach",
        "LinkedIn career tips YouTube",
        "salary negotiation tips YouTube",
        "job interview coach YouTube",
        "career growth YouTube",
        "workplace tips YouTube",
        "career advice YouTube",
    ],

    "Relationship Coach": [
        "relationship coach YouTube",
        "dating coach YouTube",
        "dating advice YouTube",
        "relationship advice YouTube",
        "marriage coach YouTube",
        "couples coaching tips YouTube",
        "love coach YouTube",
        "dating tips YouTube",
        "attraction tips YouTube",
        "social skills coach YouTube",
        "communication in relationships YouTube",
        "breakup coach tips",
        "confidence dating tips YouTube",
        "relationship tips content creator",
    ],

    # ── TIER 3: Strong fit — use YouTube to build authority/clients ──

    "Course Creator": [
        "online course creator YouTube",
        "course creation tips YouTube",
        "how to create online course YouTube",
        "digital course tips YouTube",
        "online coaching business tips",
        "membership site tips YouTube",
        "online education business tips",
        "teach online tips YouTube",
        "knowledge business YouTube",
        "course launch tips YouTube",
        "info product business YouTube",
        "online expert tips YouTube",
        "coaching program creator",
        "digital product creator YouTube",
    ],

    "LinkedIn Expert": [
        "LinkedIn tips YouTube",
        "LinkedIn marketing tips YouTube",
        "LinkedIn growth tips",
        "LinkedIn personal branding",
        "LinkedIn content strategy YouTube",
        "LinkedIn lead generation tips",
        "B2B LinkedIn tips YouTube",
        "LinkedIn for coaches",
        "LinkedIn coach YouTube",
        "thought leadership tips YouTube",
        "LinkedIn video tips",
        "personal branding YouTube",
        "professional content creator tips",
        "B2B content marketing tips",
    ],

    "Mindset & Motivation": [
        "mindset coach YouTube",
        "motivation tips YouTube",
        "success mindset YouTube",
        "discipline tips YouTube",
        "morning routine tips YouTube",
        "productivity coach YouTube",
        "habits for success YouTube",
        "self discipline coach",
        "mental toughness tips YouTube",
        "growth mindset coach YouTube",
        "manifestation coach YouTube",
        "abundance mindset YouTube",
        "motivational speaker YouTube",
        "mindset content creator",
    ],

    "B2B Consultant": [
        "business consultant YouTube",
        "B2B consultant tips YouTube",
        "strategy consultant YouTube",
        "management consultant tips YouTube",
        "business advisor YouTube",
        "operations consultant YouTube",
        "fractional CMO tips YouTube",
        "fractional CFO tips YouTube",
        "consulting business tips YouTube",
        "business systems tips YouTube",
        "process improvement tips YouTube",
        "B2B expert tips YouTube",
        "business scaling consultant",
        "consultant content creator",
    ],

    "Podcaster (video)": [
        "podcast tips YouTube",
        "podcasting for beginners YouTube",
        "how to start a podcast YouTube",
        "podcast growth tips YouTube",
        "video podcast tips",
        "podcast host YouTube",
        "podcast monetization tips",
        "business podcast tips YouTube",
        "podcast marketing tips YouTube",
        "interview podcast tips",
        "podcast content creator",
        "growing a podcast YouTube",
        "podcast production tips YouTube",
        "podcast strategy tips YouTube",
    ],

    "Social Media Expert": [
        "social media tips YouTube",
        "content creator tips YouTube",
        "Instagram growth tips YouTube",
        "TikTok growth tips YouTube",
        "YouTube growth tips",
        "social media strategy YouTube",
        "content strategy tips YouTube",
        "social media manager tips",
        "grow followers tips YouTube",
        "personal branding tips YouTube",
        "building an audience tips",
        "content creation business tips",
        "creator economy tips YouTube",
        "online presence tips YouTube",
    ],
}

# ── Dashboard dropdown ────────────────────────────────────────────────
NICHE_OPTIONS = list(NICHE_SEARCH_TERMS.keys()) + ["Custom"]


# ════════════════════════════════════════════════════════════════════
# LOCATION OPTIONS — English-speaking markets only
# ════════════════════════════════════════════════════════════════════
# All locations are English-speaking to match Fuelvia's service
# offering and ensure leads can read English cold emails.
#
# ROTATION TIP: The same niche in different locations gives
# completely different channels. YouTube search is location-aware.
# ════════════════════════════════════════════════════════════════════

LOCATION_OPTIONS = {
    "🌍 All English-speaking":           ["USA", "UK", "Canada", "Australia", "New Zealand", "South Africa"],
    "🇺🇸 United States":                 ["USA"],
    "🇬🇧 United Kingdom":                ["UK"],
    "🇨🇦 Canada":                        ["Canada"],
    "🇦🇺 Australia":                     ["Australia"],
    "🇳🇿 New Zealand":                   ["New Zealand"],
    "🇿🇦 South Africa":                  ["South Africa"],
    "🇮🇪 Ireland":                       ["Ireland"],
    "🇺🇸🇨🇦 North America":              ["USA", "Canada"],
    "🇬🇧🇮🇪 UK & Ireland":               ["UK", "Ireland"],
    "🌏 Asia-Pacific (AU + NZ)":         ["Australia", "New Zealand"],
    "🌎 Global (no location filter)":    [""],
}


# ════════════════════════════════════════════════════════════════════
# SUBSCRIBER RANGES
# ════════════════════════════════════════════════════════════════════
# Sweet spot for Fuelvia: 1K-20K subs
#   - Large enough to be serious about content (has viewers)
#   - Small enough to need editing help (not hiring in-house yet)
#   - Growing → will scale their content spend
#
# ROTATION TIP: Same niche, different range = completely different
# channels. Rotate weekly for maximum coverage without overlap.
# ════════════════════════════════════════════════════════════════════

SUBSCRIBER_RANGES = {
    "1,000 - 20,000 (RECOMMENDED)":  (1_000,   20_000),
    "1,000 - 5,000 (Micro)":         (1_000,    5_000),
    "5,000 - 10,000 (Growing)":      (5_000,   10_000),
    "10,000 - 20,000 (Established)": (10_000,  20_000),
    "20,000 - 50,000 (Mid-tier)":    (20_000,  50_000),
    "1,000 - 10,000 (Small)":        (1_000,   10_000),
    "10,000 - 30,000":               (10_000,  30_000),
    "500 - 2,000 (Nano)":            (500,      2_000),
    "50,000 - 100,000 (Large)":      (50_000, 100_000),
}


# ════════════════════════════════════════════════════════════════════
# FRESHNESS FILTER
# Filter YouTube results to channels that uploaded recently.
# "Any time" = no filter (YouTube's default relevance ranking)
# Other values = publishedAfter filter → surfaces NEW active channels
# ════════════════════════════════════════════════════════════════════
FRESHNESS_OPTIONS = {
    "Any time (default)":    None,
    "Last 7 days":           7,
    "Last 30 days":          30,
    "Last 90 days":          90,
    "Last 180 days":         180,
}


# ════════════════════════════════════════════════════════════════════
# CITY DRILLING — USA + UK + Canada + Australia
# When enabled, scraper appends city names to every keyword query.
# Each city produces a unique result pool of local creators.
# ════════════════════════════════════════════════════════════════════
CITY_DRILL_OPTIONS = {
    "🇺🇸 USA Cities (50)": [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
        "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte",
        "Indianapolis", "San Francisco", "Seattle", "Denver", "Nashville",
        "Oklahoma City", "Portland", "Las Vegas", "Memphis", "Louisville",
        "Baltimore", "Milwaukee", "Albuquerque", "Tucson", "Fresno",
        "Sacramento", "Mesa", "Kansas City", "Atlanta", "Miami",
        "Raleigh", "Minneapolis", "Cleveland", "Wichita", "Arlington",
        "Tampa", "New Orleans", "Bakersfield", "Honolulu", "Anaheim",
        "Aurora", "Santa Ana", "Corpus Christi", "Riverside", "St Louis",
    ],
    "🇬🇧 UK Cities (20)": [
        "London", "Birmingham", "Manchester", "Leeds", "Liverpool",
        "Sheffield", "Bristol", "Glasgow", "Edinburgh", "Leicester",
        "Nottingham", "Newcastle", "Cardiff", "Belfast", "Southampton",
        "Brighton", "Plymouth", "Stoke", "Coventry", "Derby",
    ],
    "🇨🇦 Canada Cities (15)": [
        "Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton",
        "Ottawa", "Winnipeg", "Quebec City", "Hamilton", "Kitchener",
        "London Ontario", "Victoria", "Halifax", "Oshawa", "Windsor",
    ],
    "🇦🇺 Australia Cities (10)": [
        "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
        "Gold Coast", "Canberra", "Hobart", "Darwin", "Newcastle NSW",
    ],
    "Disabled (use location filter only)": [],
}


# ════════════════════════════════════════════════════════════════════
# VIDEO SEARCH SUFFIXES — per niche
# These are appended to base keywords to produce title-style queries
# that surface creators who never appear in channel search results.
# ════════════════════════════════════════════════════════════════════
VIDEO_SEARCH_SUFFIXES = {
    "real_estate":        ["tour", "walkthrough", "listing", "vlog", "investing tips", "market update", "for sale"],
    "saas_tech":          ["demo", "tutorial", "review", "walkthrough", "how to use", "setup guide"],
    "business_finance":   ["tips", "advice", "strategy", "how I", "lessons learned", "my story"],
    "marketing_agency":   ["tutorial", "case study", "how to", "strategy", "results", "breakdown"],
    "coaching_courses":   ["course", "training", "coaching call", "advice", "tips", "webinar"],
    "travel_vlog":        ["vlog", "travel day", "itinerary", "trip", "explore", "hidden gems"],
    "podcast_video":      ["episode", "interview", "conversation", "discussion", "reaction"],
    "fitness_health":     ["workout", "routine", "tips", "transformation", "diet", "challenge"],
    "education":          ["explained", "tutorial", "lesson", "how to", "study", "guide"],
    "other":              ["tips", "tutorial", "how to", "guide", "review"],
}
