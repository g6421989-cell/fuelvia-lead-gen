# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## QUICK START FOR NEW SESSIONS

**PROJECT:** Fuelvia Lead Generation System v1.0  
**PURPOSE:** Automated cold email outreach to YouTube creators for video editing services  
**STATUS:** Pre-deployment testing phase (target: work.z deployment)  
**TECH STACK:** Python Flask, Notion API, YouTube API, SMTP (Hostinger), Claude API, SQLite  
**CRITICAL FILES:** app.py, notion_manager.py, scraper_engine.py, email_config.json, config.py  

**IMMEDIATE NEXT STEPS:**
1. Run pre-deployment test suite (PRE_DEPLOYMENT_TEST.md)
2. Execute 10 quick tests (email sending, rotation, limits, scraper precision, follow-ups, replies, UI, data integrity)
3. Verify 2-minute email delays and Notion updates work end-to-end
4. Fix any bugs found during testing
5. Deploy to work.z

**TO START THE SYSTEM:**
```bash
cd "D:\Chrome Downloads\Claude Powerd Lead Gen system\new lead system"
py app.py
# Open: http://127.0.0.1:5000
# Password: fuelvia2025
```

---

## SYSTEM ARCHITECTURE

### High-Level Data Flow

```
YouTube Search (API)
        ↓
Scraper Engine (scraper_engine.py)
    ├─ Filters by: niche, location, subscriber range
    ├─ Checks email existence (early filtering)
    ├─ Qualifies channels (video freshness, activity)
    ├─ Prevents duplicates (blacklist + Notion check)
        ↓
Qualified Leads → Notion Database
        ↓
Flask Dashboard (app.py) ← User Interface
    ├─ Select leads for outreach
    ├─ Trigger email campaigns
        ↓
Email Rotation Manager (_next_account)
    ├─ Cycles through 3 Hostinger accounts
    ├─ Enforces 40/account/day limit
    ├─ Enforces 2-minute delays between sends
        ↓
Claude API (claude_helpers.py)
    ├─ Writes personalized email for each lead
    ├─ Fallback template if API fails
        ↓
SMTP Send (Hostinger)
    ├─ Sends via jashan/ruwaid/danish@fuelviaa.com
    ├─ From header: "Name - Fuelvia <email@fuelviaa.com>"
        ↓
Notion Update (3 separate operations)
    ├─ update_lead_status → "Contacted" (FIRST - critical guard)
    ├─ save_day1_email_body → stores email text
    ├─ update_email_sent_from → records sending account
        ↓
IMAP Reply Detection (app.py _run_check_replies)
    ├─ Scans 3 email inboxes
    ├─ Matches replies to leads
    ├─ Updates Notion with reply content
        ↓
Follow-up Management
    ├─ Sends from SAME account as cold email
    ├─ Uses Claude to write follow-up
    ├─ Updates Day 2 Sent flag
```

### Core Components

**1. SCRAPER ENGINE (scraper_engine.py)**
- Input: niche_key, location_key, sub_range_key, max_leads
- Output: Qualified leads with: channel_name, email, subscriber_count, videos_data
- Key Logic:
  * Extracts keywords and locations from config
  * Gets subscriber range from config (min, max)
  * Creates keyword-location pairs (one at a time)
  * For each search: fetch channels → check blacklist → get details → check subscriber range → extract email → fetch videos → qualify channel → check Notion duplicate → add to qualified list
  * STOPS AT EXACT TARGET (multiple break levels)
  * Early email extraction before video fetching (75% API quota savings)
  * Blacklist persistence prevents duplicate contact attempts

**2. EMAIL ROTATION & DAILY LIMITS (app.py + daily_send_limit.py)**
- 3 Hostinger accounts: jashan@fuelviaa.com, ruwaid@fuelviaa.com, danish@fuelviaa.com
- Global counter (_email_rot_idx) cycles through accounts with thread locking
- Daily limit: SQLite database tracks sends per account per date
- Enforcement: `has_room_today(account_email)` checked BEFORE sending, `increment_today_count()` after successful send
- Limit: 40 emails per account per day (resets at midnight UTC)
- Delay: 2 minutes (120 seconds) between each send to protect new domain reputation

**3. NOTION INTEGRATION (notion_manager.py)**
- Database ID stored in config.py (NOTION_DATABASE_ID)
- Connection pooling with retry strategy (exponential backoff for transient errors)
- Key operations:
  * `get_all_leads()` - Fetches all records
  * `check_duplicate(email)` - Returns (is_duplicate, page_id)
  * `update_lead_status(page_id, status)` - Changes status field
  * `save_day1_email_body(page_id, body)` - Stores cold email text
  * `update_email_sent_from(page_id, account_email)` - Records which account sent it
  * `mark_followup1_sent(page_id)` - Sets Day 2 Sent = True, status = "Follow-up 1"
  * `mark_replied(email, reply_message)` - Updates with reply and status = "Replied"
- **CRITICAL**: All three post-send operations are in SEPARATE try/except blocks with status update running FIRST as the critical guard against double-sends

**4. CLAUDE EMAIL WRITING (claude_helpers.py)**
- Input: channel_data (subscriber_count, niche, etc) + videos (recent video info)
- Output: (subject, body) tuple
- Personalization: Uses channel metrics and video data to craft unique cold email
- Fallback: If Claude API fails (402, timeout, etc), uses generic template
- Flag: `claude_failed` set to True if fallback used, warning logged to live log

**5. FLASK DASHBOARD (app.py + dashboard_new.html)**
- Single-page app with tabbed interface
- Authentication: Password only (fuelvia2025)
- Tabs:
  * Overview: Statistics, key metrics
  * All Leads: Table view of all leads with filters
  * Emails: Email activity log
  * Replies: Reply detection results
  * Scraper: Form to start new scraping campaigns
- Live logging: Real-time event stream for all background jobs
- Background jobs: Scraping, email sending, follow-ups, reply detection (all threaded)

**6. REPLY DETECTION (app.py _run_check_replies)**
- Scans all 3 IMAP inboxes (Hostinger)
- Searches for unread emails containing "Re:" or "Fwd:"
- Extracts sender and reply text
- Matches to Notion leads via email lookup
- Updates Notion with: status = "Replied", reply content, reply date
- Note: "Reply Message " field has trailing space (Notion field name)

---

## KEY BUSINESS RULES & LIMITS

**Email Campaign Rules:**
- Max 30 leads per scrape search
- Max 40 emails per account per day (hard limit)
- 2-minute gap between each email send
- Only 2 total emails per lead: 1 cold + 1 follow-up (no 3rd email)
- If reply received: campaign ends (user manually decides next steps)

**Subscriber Range Filtering:**
- Default: 1,000 - 20,000 subscribers (RECOMMENDED)
- Other options: 1K-5K, 5K-10K, 10K-15K, 50K-100K, 100K+
- Scraper rejects any channel outside selected range
- Notion database should contain ONLY leads ≥ 1,000 subs (cleanup_low_subscribers.py removes outliers)

**Lead Statuses in Notion:**
- "New": Not contacted yet
- "Contacted": Cold email sent, awaiting response
- "Follow-up 1": Follow-up sent
- "Replied": Reply received from creator
- Blank status: Removed during database cleanup

**Domain Reputation Protection:**
- Domain (fuelviaa.com) is 1 week old → low initial reputation
- 2-minute delays prevent spam filter triggers
- Account rotation distributes load (3 accounts = 120 emails/day max total)
- Email-first filtering saves API quota (don't fetch videos for channels without email)

---

## CRITICAL FILES & THEIR PURPOSES

| File | Purpose | Critical? |
|------|---------|-----------|
| **app.py** | Flask server, all routes, email/scraper/reply threading | YES |
| **notion_manager.py** | All Notion API calls with retry logic | YES |
| **scraper_engine.py** | YouTube search, lead qualification, precision rules | YES |
| **config.py** | All configuration: API keys, niches, locations, ranges | YES |
| **email_config.json** | 3 Hostinger account credentials (SMTP) | YES |
| **claude_helpers.py** | Claude API calls for email writing | YES |
| **daily_send_limit.py** | SQLite tracking of daily email counts | YES |
| **dashboard_new.html** | Frontend UI (all tabs, forms, live logging) | YES |
| **youtube_enricher.py** | YouTube API calls for channel/video data | NO |
| **lead_intelligence.py** | Niche expansion suggestions (dashboard feature) | NO |
| **test_smtp_hostinger.py** | SMTP connection testing (verification only) | NO |
| **test_founder_names.py** | Founder name extraction testing (verification only) | NO |
| **cleanup_notion.py** | Remove non-"New" status leads (maintenance) | NO |
| **cleanup_low_subscribers.py** | Remove leads <1000 subs (maintenance) | NO |
| **PRE_DEPLOYMENT_TEST.md** | Complete test suite and checklist | NO |

---

## ENVIRONMENT & CONFIGURATION

**Environment Variables (in config.py):**
- `NOTION_API_KEY` - Notion integration token
- `NOTION_DATABASE_ID` - Notion leads database ID
- `YOUTUBE_APIS` - List of YouTube API keys (for rotation)
- `SENDER_NAME` - Default sender name if Claude fails
- `COMPANY_NAME` - "Fuelvia"

**Config Constants (in config.py):**
- `NICHE_OPTIONS` - Dict of niche keywords for search
- `LOCATION_OPTIONS` - Dict of location filters
- `SUBSCRIBER_RANGES` - Dict of subscriber range options
- `EMAIL_ROTATION_DELAY` - 120 seconds (2 minutes)
- `DASHBOARD_PASSWORD` - "fuelvia2025"
- `ADMIN_KEY` - For remote config updates

**Database Files:**
- `daily_send_limit.db` - SQLite tracking daily email counts per account
- `blacklist.db` - SQLite tracking blacklisted channel IDs (no re-contact)
- `email_config.json` - Hostinger account credentials

---

## DEPLOYMENT & TESTING

**Pre-Deployment Checklist (from PRE_DEPLOYMENT_TEST.md):**
1. PHASE 1: Email & SMTP (15 mins) - Test all 3 accounts
2. PHASE 2: Scraper Logic (20 mins) - Test max 30 limit, precision, blacklist
3. PHASE 3: Cold Email Campaign (10 mins) - Test send, logging, Notion updates
4. PHASE 4: Follow-ups (10 mins) - Test follow-up send and Notion updates
5. PHASE 5: Reply Detection (5 mins) - Test IMAP scanning
6. PHASE 6: Dashboard UI (5 mins) - Test all tabs and responsiveness
7. QUICK TESTS (10 tests, 5 mins each)
8. CRITICAL CHECKS (12 must-have working, 13 must-NOT-have)
9. PERFORMANCE BENCHMARKS (6 metrics)
10. DEPLOYMENT CHECKLIST (20+ sign-off items)

**Common Commands:**
```bash
# Start server
py app.py

# Test SMTP (all 3 accounts)
py test_smtp_hostinger.py

# Test founder name extraction
py test_founder_names.py

# Clean up non-"New" leads
py cleanup_notion.py

# Clean up low-subscriber leads
py cleanup_low_subscribers.py

# Check server log
tail -100 server.log

# Stop server (Windows)
taskkill /F /IM python.exe
```

---

## KNOWN ISSUES & FIXES APPLIED

**FIXED BUGS:**
1. ✅ Double-email bug - Separated Notion updates into 3 independent try/except blocks
2. ✅ Claude API failure - Added claude_failed flag and fallback template
3. ✅ No daily limit - Implemented SQLite tracking with has_room_today()
4. ✅ Hardcoded target leads - Made scraper accept max_leads parameter
5. ✅ Follow-up skip when blank - Added explicit warning if Email Sent From is blank
6. ✅ Founder names not personalized - Added dynamic extraction from email addresses
7. ✅ Scraper overshooting - Implemented multiple break levels and target_reached flag
8. ✅ API quota waste - Added email-first filtering (extract email before fetching videos)
9. ✅ Max 30 validation - Added frontend max="30" + backend 400 error for >30

**CURRENT ISSUES:**
- None known; system ready for pre-deployment testing

---

## DEVELOPER NOTES

**Email Rotation Logic:**
- Global counter `_email_rot_idx` increments after each send
- Thread-safe with `_email_rot_lock`
- Formula: `account = OUTREACH_ACCOUNTS[_email_rot_idx % 3]`
- Cycles: jashan → ruwaid → danish → jashan ...

**Double-Email Prevention:**
The critical protection is: Status update FIRST, other updates AFTER
```python
try:
    notion.update_lead_status(lead["id"], "Contacted")  # FIRST
except:
    log_error()
    # Still proceed to next lead
```
If status update fails, lead stays "New" and won't be re-sent (because it's still "New" on next check)

**Notion Property Names:**
- Standard fields: "Channel Name", "Email", "Status", "Subscriber Count", etc.
- Special: "Reply Message " has TRAILING SPACE (match Notion field exactly)

**Scraper Precision Rules:**
1. Max 30 leads per search (hard limit)
2. Stop at exact target (multiple break levels)
3. One keyword-location combo at a time
4. Break ALL loops at target
5. Check email BEFORE qualification (API savings)
6. Live log: "Found X of Y requested leads"
7. Graceful exhaustion message

**Rate Limiting & Quotas:**
- YouTube API: 4 keys with rotation for quota management
- Notion API: Retry strategy with exponential backoff
- SMTP: 40 emails/account/day, 2-minute gaps between sends
- Claude API: Fallback template if fails

---

## NEXT IMMEDIATE STEPS

1. **Run complete pre-deployment test suite** (PRE_DEPLOYMENT_TEST.md)
   - 10 quick tests covering all functionality
   - 12 critical checks (must be working)
   - 13 critical anti-checks (must NOT happen)
   - Performance benchmarks

2. **Fix any bugs discovered during testing**

3. **Deploy to work.z**
   - Update target URL in documentation
   - Verify production Notion database is connected
   - Verify production email accounts are working
   - Run final sanity check

4. **Monitor first 3 days of live operation**
   - Watch email delivery rates
   - Watch for bounces
   - Monitor reply rates
   - Check Notion updates are happening

---

## SESSION HANDOFF NOTES

This system has been extensively tested in development. The 3 Hostinger email accounts are configured, all SMTP connections pass, Notion API is integrated, Claude API fallback is working, and the 2-minute delay enforcement is in place.

The last session completed:
- Fixed all known bugs
- Implemented 2-minute delays between emails
- Added comprehensive logging with Notion update confirmations
- Cleaned Notion database (removed non-"New" and <1000 subscriber leads)
- Verified all 5 critical verification checks PASS
- Created pre-deployment test suite (PRE_DEPLOYMENT_TEST.md)

The immediate next action is to run the complete test suite and fix any issues found. System should be production-ready after testing phase.
