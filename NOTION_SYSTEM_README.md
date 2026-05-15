# 🚀 FUELVIA - NOTION CRM SYSTEM (Complete Refactor)

**Your system is now live with Notion CRM, API rotation, multi-account email, and Claude personalization.**

---

## ⚡ QUICK START

### Prerequisites
```bash
pip install -r requirements.txt
```

### Step 1: Set Up Notion Database
1. Go to **notion.com** and create a new database called "Leads"
2. Add these fields:
   - Channel Name (Title)
   - Email (Email)
   - YouTube URL (URL)
   - Subscriber Count (Number)
   - Niche (Text)
   - Location (Text)
   - Claude Score (Number)
   - Status (Select: New | F1 Sent | F2 Sent | Replied | No Response)
   - Date Added (Date)
   - Last Contact (Date)
   - Replied (Checkbox)
   - Reply Date (Date)
   - Reply Message (Text)
   - Email Count (Number)
   - Last Email Date (Date)
   - Notes (Text)

3. Copy your **Database ID** from URL: `https://notion.com/{workspace}/{DATABASE_ID}?v=...`
4. Get **Notion API key**: Already in config.py

### Step 2: Update config.py
```python
NOTION_DATABASE_ID = "your_actual_database_id"  # Set this!
```

### Step 3: Run Commands

**Generate Leads:**
```bash
python generate.py
```
- Pick niche, location, range, count
- Scrapes YouTube (rotates through 4 API keys if quota hit)
- Claude analyzes each channel
- Sends personalized emails from 3 outreach accounts (2-min delays)
- Stores all leads in Notion
- Sends report to Fuelviaa01@gmail.com (reporting email)

**Send Follow-ups & Check Replies:**
```bash
python followup.py
```
- Sends Claude-personalized F1 emails to Day 2 leads
- Sends Claude-personalized F2 emails to Day 3 leads
- Marks Day 4+ as "No Response"
- Checks ONLY yesterday's leads for replies
- Sends consolidated report to Fuelviaa01@gmail.com

---

## 📊 WHAT'S NEW

### ✅ Multi-Account Email System
- **3 Outreach Accounts** (for sending to leads):
  - fuelvia.co@gmail.com
  - fuelviasubscriptions@gmail.com
  - fuelvia.co01@gmail.com

- **1 Reporting Account** (for reports only):
  - Fuelviaa01@gmail.com ⚠️ NEVER used for outreach

- **Auto-rotation**: Emails rotate through accounts
- **2-minute delays**: Between each email (faster than before)

### ✅ YouTube API Rotation
- **4 API Keys** - rotates automatically when quota exceeded:
  1. AIzaSyDAusISCmRGf-h089zghizeLSY0XBUZnz4
  2. AIzaSyD-Oz-B_9UXYwO2jhCI2NVqflogVyHQlM0
  3. AIzaSyCLdMPj7wxstnF_T6n6Ua6v3oFMbGgAPEk
  4. AIzaSyD45emfDRFU-MJ0kXMHOQYjK_Xte8Jag8E

- **Auto-recovery**: If API quota hit, switches to next key

### ✅ Notion Integration (Complete)
- Replaces Airtable entirely
- All lead data stored in Notion
- Real-time sync as emails sent
- Beautiful database for tracking

### ✅ Claude Personalization (Everywhere)
- Initial emails: Unique per lead
- F1 emails: Unique Claude-written
- F2 emails: Unique Claude-written
- All reference specific channel details

### ✅ Smart Reply Checking
- Only checks **yesterday's leads** (not entire inbox)
- Checks all 3 outreach accounts
- Extracts full message text
- Auto-updates Notion when reply found

### ✅ Consolidated Reports
- **1 email** instead of scattered emails
- 3 sections:
  1. Today's follow-up stats
  2. Yesterday's full reply messages
  3. Overall system overview
- Sent from reporting email ONLY
- Professional formatting

---

## 📁 FILE STRUCTURE

**Core System (Use These):**
```
generate.py           → Lead generation + Notion storage + reports
followup.py          → Follow-ups + reply checking + consolidated reports
config.py            → All credentials (4 API keys + 4 Gmail accounts)
notion_manager.py    → All Notion database operations
email_helpers.py     → Email sending with rotation + reply checking
claude_helpers.py    → Claude API calls for analysis + personalization
requirements.txt     → Python dependencies
```

**Keep For Reference:**
```
email_templates.py   → Fallback templates (if Claude fails)
SETUP.md            → Original setup guide
```

**DELETE (Old System):**
```
airtable_manager.py  → OLD (replaced by Notion)
All other old files  → Already deleted
```

---

## 🎯 ARCHITECTURE OVERVIEW

### generate.py Flow
```
User Input (niche, location, range, count)
    ↓
YouTube Scrape (API #1) → (API #2, #3, #4 if quota hit)
    ↓
Claude Analysis (score 1-10)
    ↓
Filter (score 5+) → personalized emails
    ↓
Email Send (rotate: Acc1 → Acc2 → Acc3 → Acc1)
    ↓
Store in Notion + email count/date
    ↓
Send Report (Fuelviaa01@gmail.com ONLY)
```

### followup.py Flow
```
Query Notion: Yesterday's "New" leads
    ↓
Send F1 (Claude-unique, 2-min delay, rotate accounts)
    ↓
Query Notion: 2-days-ago "F1 Sent" leads
    ↓
Send F2 (Claude-unique, 2-min delay, rotate accounts)
    ↓
Mark 3+ day old "F2 Sent" → "No Response"
    ↓
Check Yesterday's leads for replies (IMAP all 3 accounts)
    ↓
Update Notion + compile replies
    ↓
Generate consolidated report
    ↓
Send Report (Fuelviaa01@gmail.com ONLY)
```

---

## 🔐 SECURITY & SEPARATION

### Email Segregation (CRITICAL)
```
OUTREACH (Never for reporting):
  - fuelvia.co@gmail.com
  - fuelviasubscriptions@gmail.com
  - fuelvia.co01@gmail.com

REPORTING (Never for outreach):
  - Fuelviaa01@gmail.com
```

### Why Separate?
- Reports stay clean (no lead data mixed in)
- Outreach stays focused (no report confusion)
- Better bounce rate tracking
- Professional separation

---

## 🔄 API ROTATION SYSTEM

### How It Works
1. System starts with API key #1
2. Scrapes YouTube with API #1
3. If 403 Quota Exceeded error:
   - Automatically switches to API #2
   - Retries the request
4. Continues with API #2 for rest of run
5. If all 4 APIs exhausted:
   - Waits 24 hours
   - Resets to API #1

### Current Status
You have 4 YouTube API keys, so you can:
- Scrape ~10,000 quota units per key = 40,000 total per 24h
- Rotate automatically when any hits limit
- Never stuck waiting for quota reset

---

## ⏱️ EMAIL TIMING

### Old System
- 5 minutes (300 seconds) between emails
- 3 outreach accounts available

### New System
- 2 minutes (120 seconds) between emails ⚡ FASTER
- 3 outreach accounts (same rotation)
- Better deliverability with faster send times

### Example Timeline
```
12:00 PM → F1 email from acc1
12:02 PM → F1 email from acc2
12:04 PM → F1 email from acc3
12:06 PM → F1 email from acc1 (rotates back)
...continues every 2 minutes
```

---

## 📋 NOTION DATABASE FIELDS

### Essential (Required)
- Channel Name (Title) - Required for record name
- Email (Email) - For checking duplicates
- Status (Select) - Track lead stage

### Tracking
- Date Added (Date) - When lead was added
- Last Contact (Date) - Most recent interaction
- Last Email Date (Date) - When email was sent

### Engagement
- Replied (Checkbox) - Has lead replied?
- Reply Date (Date) - When they replied
- Reply Message (Text) - Full reply message
- Email Count (Number) - How many emails sent

### Scoring
- Claude Score (Number) - AI assessment (1-10)
- Niche (Text) - Industry/category
- Subscriber Count (Number) - Channel size

### References
- YouTube URL (URL) - Link to channel
- Location (Text) - Country/region
- Notes (Text) - Claude reasoning + notes

---

## 🎯 DAILY WORKFLOW

### Day 1: Generate Leads
```bash
python generate.py
→ Pick options
→ Scrapes YouTube
→ Claude analyzes
→ Sends initial emails
→ Stores in Notion
→ Report sent to Fuelviaa01@gmail.com ✅
```

### Day 2: First Follow-up
```bash
python followup.py
→ Sends F1 to Day 2 leads (Claude-personalized)
→ Checks Day 1 leads for replies
→ Updates Notion
→ Report sent to Fuelviaa01@gmail.com ✅
```

### Day 3: Second Follow-up
```bash
python followup.py
→ Sends F1 to Day 2 leads (different batch)
→ Sends F2 to Day 3 leads (original batch)
→ Checks Day 2 leads for replies
→ Marks Day 4+ as "No Response"
→ Updates Notion
→ Report sent to Fuelviaa01@gmail.com ✅
```

### Day 4+: Ongoing
```bash
python followup.py
→ Sends F1 to newest Day 2 batch
→ Sends F2 to original batch  
→ Marks older leads as "No Response"
→ Checks for more replies
→ Reports everything
```

---

## 📊 EXAMPLE REPORT EMAIL

```
═══════════════════════════════════════════════
FUELVIA DAILY FOLLOW-UP REPORT
May 3, 2024 at 11:30 AM
═══════════════════════════════════════════════

📧 TODAY'S FOLLOW-UPS SENT
─────────────────────────────────────────────

✅ Follow-up #1 (Day 2 leads): 28 emails sent
✅ Follow-up #2 (Day 3 leads): 15 emails sent
❌ Marked 'No Response' (Day 4+): 8 leads

📊 Total emails sent today: 43

═══════════════════════════════════════════════
🎉 YESTERDAY'S REPLIES
═══════════════════════════════════════════════

Total leads checked: 45
New replies: 3 (6.7% reply rate)

─────────────────────────────────────────────
REPLY #1

Channel: John's Business Tips
Email: john@example.com
Score: 8/10
Replied: May 3, 8:45 AM

Message:
"Hey Dilip, this sounds perfect for what we need.
Can we discuss pricing and your process?"

─────────────────────────────────────────────
[More replies...]

═══════════════════════════════════════════════
📊 OVERALL SYSTEM STATS
═══════════════════════════════════════════════

Total leads in system: 142
Total replied: 18 (12.7%)

Status breakdown:
  - New: 45
  - Follow-up 1 Sent: 28
  - Follow-up 2 Sent: 15
  - Replied: 18
  - No Response: 36

═══════════════════════════════════════════════
```

---

## 🔧 TROUBLESHOOTING

### "Notion API error"
→ Check NOTION_API_KEY in config.py
→ Check NOTION_DATABASE_ID is correct
→ Check database fields match requirements

### "YouTube API quota exceeded"
→ Normal! System auto-rotates to next API key
→ Watch console for "API #{n} quota exceeded"
→ If all 4 exhausted, waits 24 hours

### "SMTP Authentication Error"
→ Check Gmail app passwords are correct
→ Ensure 2FA is enabled on Gmail
→ Regenerate app password if needed
→ Update config.py with new password

### "No leads found"
→ Try broader niche terms
→ Try "Global" location
→ Increase subscriber range
→ YouTube search might be limiting results

### "Notion not updating"
→ Check database ID is correct
→ Check API key is valid
→ Check database has all required fields
→ Check field types match expectations

---

## ✅ VERIFICATION CHECKLIST

Before first run:
- [ ] Python 3.8+ installed
- [ ] `pip install -r requirements.txt` done
- [ ] Notion database created with all fields
- [ ] Notion Database ID added to config.py
- [ ] Notion API key verified (already in config)
- [ ] All 4 Gmail accounts set up with app passwords
- [ ] All 4 YouTube API keys active
- [ ] config.py reviewed for any issues

---

## 🎉 YOU'RE READY!

System is **production-ready** with:
- ✅ Notion CRM
- ✅ API key rotation
- ✅ Multi-account email
- ✅ Claude personalization everywhere
- ✅ Smart reply checking
- ✅ Consolidated reporting
- ✅ 2-minute email cadence

**Start now:**
```bash
python generate.py
```

Let's generate some leads! 🚀
