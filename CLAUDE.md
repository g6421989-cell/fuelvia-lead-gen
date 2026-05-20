# CLAUDE.md — Fuelvia Lead Generation System
# PROJECT MEMORY — Read this first in every new session. Do NOT re-read individual files.

---

## ⚡ INSTANT CONTEXT

**What this is:** Automated YouTube cold email outreach system for Fuelvia (video editing agency).
**Owner:** Dilip / Fuelvia team — domain: fuelviaa.com — SMTP: Hostinger
**Location:** `D:\Chrome Downloads\Claude Powerd Lead Gen system\new lead system\`
**Start:** Double-click `Start Fuelvia.bat` → `http://127.0.0.1:5000` → password: `fuelvia2025`
**Status:** ✅ Production-ready. All bugs fixed. Pre-deployment tested.

---

## 🗺️ USE GRAPHIFY — NEVER RE-READ FILES

A persistent knowledge graph lives at `graphify-out/`. Query it instead of opening .py files:

```bash
/graphify query "how does email sending work"
/graphify query "how does the scraper find leads"
/graphify query "how does reply detection work"
/graphify explain "NotionManager"
/graphify path "scrape_leads" "NotionManager"
```

Graph stats: **480 nodes · 729 edges · 38 communities** (AST extraction, 2026-05-19)
Files: `graphify-out/graph.json` · `graphify-out/graph.html` · `graphify-out/GRAPH_REPORT.md`

After any code changes: `/graphify "D:\Chrome Downloads\Claude Powerd Lead Gen system\new lead system" --update`

---

## 🏗️ ARCHITECTURE — Full Data Flow

```
YouTube API (4 keys, auto-rotating)
        ↓
scraper_engine.py → scrape_leads() [GENERATOR]
    ├─ Dual search: channel search + video search (3-5x more leads)
    ├─ channel_qualifier.py  ← email-first (extract before video fetch = 75% API savings)
    ├─ smart_scorer.py + cta_detector.py  ← intelligent lead scoring
    ├─ channel_blacklist.py  ← SQLite, permanent no-re-contact
    └─ Stops at EXACT target (multiple break levels)
        ↓
notion_manager.py → Notion Database (CRM)  ← GOD NODE degree 51
        ↓
app.py (Flask dashboard)
    ├─ Auth: _auth() decorator — session-based, password only
    ├─ Security: security.py — bot/UA detection, IP blocklist, decoy page
    ├─ Routes: /api/leads, /api/start-scrape, /api/send-emails, etc.
    ├─ Live log: SSE stream at /stream (real-time to dashboard)
    └─ Background threads: scraper, email sender, followup, reply checker
        ↓
claude_helpers.py → write_personalized_initial_email() / write_personalized_followup_1()
    └─ Fallback template if Claude API fails (claude_failed flag)
        ↓
email_helpers.py → EmailRotator → _smtp_send()
    ├─ 3 Hostinger accounts: jashan / ruwaid / danish @fuelviaa.com
    ├─ SMTP timeout=30 (CRITICAL — prevents 2-min hangs on dead connections)
    ├─ 2-minute delay between sends (EMAIL_ROTATION_DELAY = 120s)
    └─ 40 emails/account/day (daily_send_limit.py SQLite)
        ↓
Notion Update — 3 SEPARATE try/except blocks (never chain these):
    1. update_lead_status("Contacted")  ← FIRST — double-send guard
    2. save_day1_email_body()
    3. update_email_sent_from()
        ↓
followup.py → FollowupSystem
    ├─ Uses SAME account as original cold email (Email Sent From field)
    ├─ Claude writes follow-up
    └─ Marks Day 2 Sent = True in Notion
        ↓
email_helpers.py → ReplyChecker (IMAP)
    ├─ Scans all 3 Hostinger inboxes
    ├─ Matches sender email → Notion lead record
    └─ mark_replied() → status = "Replied" + stores reply text
```

---

## 📁 FILE MAP — Every File and What It Does

### Core
| File | Role | Graph Degree |
|------|------|-------------|
| `app.py` | Flask server, ALL routes, background threads, SSE | 19 (_auth) |
| `config.py` | All constants: API keys, niches, locations, limits | — |
| `config_secure.py` | Secure loader: `get_outreach_accounts()`, `get_youtube_api_keys()` | — |

### Email Pipeline
| File | Role |
|------|------|
| `email_helpers.py` | `EmailRotator` (3 accounts), `send_outreach_email()`, `ReplyChecker` IMAP |
| `followup.py` | `FollowupSystem`: send follow-up 1, check replies, mark closed |
| `email_templates.py` | Fallback templates: initial, followup_1, followup_2 |
| `email_compliance.py` | `EmailCompliance`: unsubscribe tokens, bounce log, GDPR footer |
| `claude_helpers.py` | `write_personalized_initial_email()` + `write_personalized_followup_1()` |

### Scraping & Qualification
| File | Role | Graph Degree |
|------|------|-------------|
| `scraper_engine.py` | `scrape_leads()` generator — dual YouTube search | 11 |
| `channel_qualifier.py` | `qualify_channel()`: email extract + hard/soft filters, score 0-7 | — |
| `smart_scorer.py` | `intelligent_score_channel()`: engagement, activity, upload freq | 11 |
| `cta_detector.py` | `score_ctas()`, `score_b2b_language()`, `has_entertainment_focus()` | — |
| `youtube_enricher.py` | `get_videos_for_channel()`, `days_since_last_video()` | — |
| `channel_blacklist.py` | SQLite blacklist (`channel_blacklist.db`) | — |

### Notion CRM
| File | Role | Graph Degree |
|------|------|-------------|
| `notion_manager.py` | `NotionManager` class — ALL Notion CRUD, retry logic | **51 (most connected)** |

### Data & Limits
| File | Role |
|------|------|
| `daily_send_limit.py` | SQLite per-account daily counter (`daily_send_limit.db`) |
| `quota_manager.py` | YouTube API quota tracker (`quota_data.json`) |
| `backup_manager.py` | SQLite backups of leads/emails/replies (`leads_backup.db`) |
| `lead_intelligence.py` | Niche health, expansion suggestions, lead freshness |
| `error_logger.py` | `ErrorLogger`: structured logs + alert emails on critical errors |

### Security & Maintenance
| File | Role |
|------|------|
| `security.py` | `@check_suspicious_request` decorator, bot/UA detection, decoy page |
| `cleanup_notion.py` | Remove non-"New" leads from Notion |
| `cleanup_low_subscribers.py` | Archive leads with <1000 subscribers |
| `run_audit.py` | Full system health audit |
| `airtable_manager.py` | Legacy (replaced by Notion — do not use) |

### Old Scrapers — ARCHIVED, do NOT use
`generate.py`, `generate_v2.py`, `generate_v3.py` — all superseded by `scraper_engine.py`

---

## ⚙️ CONFIGURATION

### API Keys — config.py / .env
```python
NOTION_API_KEY       = "secret_..."   # notion.so/my-integrations
NOTION_DATABASE_ID   = "..."          # 32-char DB ID from URL
YOUTUBE_APIS         = ["AIza..."]    # 4 keys, rotated on quota error
CLAUDE_API_KEY       = "sk-ant-..."   # via aicredits.in proxy
```

### Email Accounts — email_config.json
```json
{ "outreach_emails": [
    { "email": "jashan@fuelviaa.com",  "smtp_server": "smtp.hostinger.com", "smtp_port": 587 },
    { "email": "ruwaid@fuelviaa.com",  "smtp_server": "smtp.hostinger.com", "smtp_port": 587 },
    { "email": "danish@fuelviaa.com",  "smtp_server": "smtp.hostinger.com", "smtp_port": 587 }
]}
```

### Limits — config.py
```python
EMAIL_ROTATION_DELAY          = 120   # seconds between sends
MAX_EMAILS_PER_ACCOUNT_PER_DAY = 40  # 120/day total
MAX_LEADS_PER_SCRAPE          = 30    # hard cap
DASHBOARD_PASSWORD            = "fuelvia2025"
ADMIN_KEY                     = "..."
```

---

## 📊 NOTION DATABASE SCHEMA

**Status flow:** New → Contacted → Follow-up 1 → Follow-up 2 → Replied → Closed

| Field | Type | Notes |
|-------|------|-------|
| Channel Name | title | — |
| Email | email | — |
| Status | select | See flow above |
| Subscriber Count | number | — |
| YouTube URL | url | — |
| Niche | select | — |
| Location | select | — |
| Day 1 Email Body | rich_text | Stored after send |
| Email Sent From | email | Which account sent it |
| Day 2 Sent | checkbox | Follow-up sent flag |
| Reply Message  | rich_text | ⚠️ TRAILING SPACE in field name |
| Reply Date | date | — |
| Last Contact | date | — |

---

## 🔑 CRITICAL RULES — Never Break

1. **Status update FIRST** — `update_lead_status("Contacted")` before logging send result → prevents double-send on crash
2. **SMTP timeout=30** — always. Without it dead connections hang for 120s
3. **3 separate try/except** for post-send Notion updates — never chain them
4. **Follow-up = same account** as cold email — read `Email Sent From` field
5. **Max 2 emails per lead** — cold + 1 follow-up. Block any 3rd attempt
6. **Email-first filter** — extract email from description BEFORE fetching videos
7. **`Reply Message ` has trailing space** — match Notion field name exactly

---

## 🐛 BUGS FIXED (do not reintroduce)

| Bug | Fix |
|-----|-----|
| SMTP hangs 2 min on failure | `timeout=30` on `smtplib.SMTP()` |
| Double email send on crash | Status → "Contacted" FIRST in its own try/except |
| Claude API 402/timeout | `claude_failed` flag + fallback template |
| No daily send limit | SQLite tracking in `daily_send_limit.py` |
| Scraper overshooting target | `target_reached` flag + multiple break levels |
| API quota wasted on no-email channels | Email extracted before video fetch |
| Follow-up from wrong account | `Email Sent From` lookup before send |
| `_smtp_send` returned bool only | Changed to `(bool, error_str)` tuple, logs actual error |

---

## 🖥️ COMMON COMMANDS

```bash
py app.py                          # Start server
py test_smtp_hostinger.py          # Test all 3 SMTP accounts
py cleanup_notion.py               # Remove non-New leads
py cleanup_low_subscribers.py      # Remove <1000 sub leads
py run_audit.py                    # Full health audit

# Quick checks
py -c "from daily_send_limit import get_all_today_counts; print(get_all_today_counts())"
py -c "from quota_manager import get_quota; print(get_quota())"

# Kill server (Windows)
taskkill /F /IM py.exe
```

---

## 🗂️ GRAPH COMMUNITY LABELS (38 communities)

| # | Community Focus |
|---|----------------|
| 0 | Email send pipeline + daily limits + YouTube enricher |
| 1 | Flask API routes (send, scrape, dashboard) |
| 2 | Follow-up system + IMAP reply checker |
| 3 | CTA detector + smart scorer |
| 4 | Email compliance (GDPR, unsubscribe, bounce) |
| 5 | Secure config + error logger/alerts |
| 6 | Channel blacklist + scraper engine core |
| 7 | NotionManager CRUD operations |
| 8 | Security layer (bot detection, decoy) |
| 9 | Email rotator + send helpers |
| 11 | Dashboard API + NotionManager hub (highest traffic) |
| 17 | Claude AI email writing |

---

## 📂 FULL DIRECTORY

```
new lead system\
├── app.py                     ← Main Flask server
├── config.py                  ← All config
├── config_secure.py           ← Credential loader
├── scraper_engine.py          ← YouTube scraper (USE THIS)
├── notion_manager.py          ← Notion CRM (degree 51)
├── claude_helpers.py          ← AI email writer
├── email_helpers.py           ← SMTP + IMAP + rotation
├── followup.py                ← Follow-up system
├── email_compliance.py        ← GDPR compliance
├── channel_qualifier.py       ← Lead qualification
├── smart_scorer.py            ← Lead scoring
├── cta_detector.py            ← B2B detection
├── youtube_enricher.py        ← YouTube API calls
├── channel_blacklist.py       ← SQLite blacklist
├── daily_send_limit.py        ← Daily email counters
├── quota_manager.py           ← API quota tracker
├── security.py                ← Bot detection
├── error_logger.py            ← Logging + alerts
├── backup_manager.py          ← SQLite backups
├── lead_intelligence.py       ← Niche analytics
├── email_config.json          ← SMTP credentials
├── Start Fuelvia.bat          ← Windows launcher
├── graphify-out/              ← KNOWLEDGE GRAPH (query this)
│   ├── graph.json
│   ├── graph.html
│   └── GRAPH_REPORT.md
└── templates/
    └── dashboard_new.html     ← Frontend UI
```

---

## ✅ NEW SESSION CHECKLIST

1. Read THIS file → you have full context, no file reading needed
2. Specific function questions → `/graphify query "..."`
3. After code changes → `/graphify ... --update`
4. Do NOT open individual .py files unless making a specific edit
5. Check `server.log` for recent errors before touching anything

---

*Graph: 480 nodes · 729 edges · 38 communities · AST · 2026-05-19*
*Stack: Python Flask · Notion API · YouTube API · Hostinger SMTP · Claude API · SQLite*
