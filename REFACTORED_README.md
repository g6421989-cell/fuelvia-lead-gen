# 🚀 FUELVIA REFACTORED - 2-COMMAND SYSTEM

**Your lead generation system is now simplified into 2 commands.**

---

## 📋 QUICK START

### Command 1: Generate Leads
```bash
python generate.py
```
**What it does:**
- Asks for niche, location, subscriber range, and how many leads to scrape
- Scrapes YouTube for channels matching your criteria
- Claude AI scores each channel (1-10 scale)
- Filters qualified leads (score 5+/10)
- Sends **Claude-personalized initial emails** (not templates)
- Saves all leads to Airtable
- **Sends instant notification email** when complete

**Time:** 10-30 minutes depending on lead count

**Output Email:** 
- Subject: `✅ Lead Generation Complete - X Emails Sent`
- Shows: Channels analyzed, qualified count, emails sent, timestamp
- Sent to: Your personal email

---

### Command 2: Follow-ups & Replies
```bash
python followup.py
```
**What it does:**
- Sends **Claude-personalized Follow-up #1** to Day 2 leads (using Claude, not templates)
- Sends **Claude-personalized Follow-up #2** to Day 3 leads (using Claude, not templates)
- Marks Day 4+ leads as "No Response"
- **Checks ONLY yesterday's leads for replies** (not all emails)
- Extracts full reply messages with timestamps
- Generates **ONE consolidated email** with 3 sections:
  1. Today's follow-up stats (F1, F2, No Response counts)
  2. Yesterday's replies with full messages and channel details
  3. Overall system statistics (total leads, reply rate, status breakdown)

**Time:** 10-20 minutes depending on lead count

**Output Email:** 
- Subject: `📊 Follow-up Complete - X Emails Sent, Y Replies`
- Contains: Full follow-up stats, all reply messages, system overview
- Sent to: Your personal email

---

## 📅 RECOMMENDED WORKFLOW

### Day 1: Generate Leads
```bash
python generate.py
→ Pick niche, location, range → Scrapes YouTube → Claude analyzes → Sends emails
→ Receive notification email ✅
```

### Day 2: First Follow-up (if needed)
```bash
python followup.py
→ Sends F1 to Day 2 leads → Checks yesterday's replies
→ Receive consolidated report email ✅
```

### Day 3: Second Follow-up (if needed)
```bash
python followup.py
→ Sends F1 to Day 2 leads, F2 to Day 3 leads → Checks yesterday's replies
→ Receive consolidated report email ✅
```

### Day 4+: Automatic No Response Marking
- Leads that don't reply by Day 4 are auto-marked as "No Response"
- Every `followup.py` run updates this status

---

## 🎯 KEY FEATURES

### ✨ Personalized Emails with Claude
- **Initial emails:** Claude analyzes channel and writes personalized pitch
- **Follow-up #1:** Claude personalizes based on channel niche and score
- **Follow-up #2:** Claude creates urgency while staying friendly

### 📊 Consolidated Reports
Instead of cluttered daily emails, you get **ONE beautifully formatted email** with:
- All follow-up stats in one place
- Full reply messages from leads (not just previews)
- Complete system overview
- No need to check multiple sources

### 🎯 Smart Reply Checking
- Only checks **yesterday's leads** (not entire inbox)
- Prevents duplicate notifications
- Extracts full message text
- Updates Airtable automatically

### ⏰ Runs When You Want
- No background scheduler needed
- Just run `python followup.py` when ready
- No laptop needs to be on 24/7
- Manual control = better efficiency

---

## 📁 FILES IN YOUR SYSTEM

### NEW FILES (Use these)
- **generate.py** - Lead generation with instant notification
- **followup.py** - Follow-ups + reply checking + consolidated report

### EXISTING FILES (Still used, don't delete)
- **config.py** - Your credentials and settings
- **airtable_manager.py** - Database operations
- **email_templates.py** - Fallback templates (if Claude fails)
- **requirements.txt** - Python packages

### OLD FILES (Can be deleted or ignored)
- ~~start.py~~ - No longer needed
- ~~scheduler.py~~ - No longer needed
- ~~daily_reporter.py~~ - Logic moved into followup.py
- ~~reply_monitor.py~~ - Logic moved into followup.py
- ~~lead_generator.py~~ - Logic moved into generate.py
- ~~followup_system.py~~ - Logic moved into followup.py
- ~~test.py~~ - Empty/junk
- ~~hello.py~~ - Junk file

---

## 🔧 TECHNICAL DETAILS

### generate.py
```
├─ get_user_inputs()          → Ask niche, location, range, count
├─ scrape_youtube_leads()     → Search YouTube API
├─ analyze_channel()           → Claude scores each channel (1-10)
├─ analyze_and_filter_leads()  → Keep only score 5+/10
├─ write_personalized_email()  → Claude writes initial email
├─ send_email()                → Send via Gmail SMTP + rotation
└─ send_notification_email()   → Instant notification when done
```

### followup.py
```
├─ send_followup_1()           → Claude personalizes + sends F1
├─ send_followup_2()           → Claude personalizes + sends F2
├─ mark_no_response()          → Day 4+ → "No Response"
├─ check_yesterday_replies()   → IMAP search only yesterday's emails
├─ get_system_stats()          → Airtable stats
├─ generate_consolidated_report_email() → Format 3-section email
└─ send_consolidated_report()  → Send ONE email with everything
```

---

## 📧 EMAIL EXAMPLES

### generate.py Output Email
```
Subject: ✅ Lead Generation Complete - 23 Emails Sent

Lead Generation Complete!

═══════════════════════════════════════════════

📊 CAMPAIGN SUMMARY

Channels analyzed: 87
Qualified (score 5+/10): 35
Emails sent: 23
Timestamp: May 3, 2024 at 02:45 PM

═══════════════════════════════════════════════

✅ All leads have been added to Airtable.

Next steps:
1. Run 'python followup.py' tomorrow to send day 2 follow-ups
2. Monitor replies in your Gmail inbox
3. Check Airtable for lead details and Claude scores

© Fuelvia System
```

### followup.py Output Email
```
Subject: 📊 Follow-up Complete - 43 Emails Sent, 3 Replies

═══════════════════════════════════════════════
FUELVIA DAILY FOLLOW-UP REPORT
May 3, 2024 at 11:30 AM
═══════════════════════════════════════════════

📧 TODAY'S FOLLOW-UPS SENT
───────────────────────────────────────────────

✅ Follow-up #1 (Day 2 leads): 28 emails sent
✅ Follow-up #2 (Day 3 leads): 15 emails sent
❌ Marked 'No Response' (Day 4+): 8 leads

📊 Total emails sent today: 43

═══════════════════════════════════════════════
🎉 YESTERDAY'S REPLIES
═══════════════════════════════════════════════

Total leads checked: 45
New replies: 3 (6.7% reply rate)

───────────────────────────────────────────────
REPLY #1

Channel: John's Business Tips
Email: john@businesstips.com
Score: 8/10
Replied: May 3, 8:45 AM

Message:
"Hey Dilip, thanks for reaching out! This sounds perfect 
for where we're at. Would love to chat this week about 
your process and pricing. Are you free?"

───────────────────────────────────────────────
[More replies...]

═══════════════════════════════════════════════
📊 OVERALL SYSTEM STATS
═══════════════════════════════════════════════

Total leads in system: 142
Total replied: 18 (12.7%)

Status breakdown:
  - New (Day 1): 45
  - Follow-up #1 Sent (Day 2): 28
  - Follow-up #2 Sent (Day 3): 15
  - Replied: 18
  - No Response: 36

═══════════════════════════════════════════════
```

---

## ⚙️ INSTALLATION & SETUP

### Step 1: Verify Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Update config.py (if needed)
- Verify AIRTABLE_BASE_ID is set
- Verify Gmail app passwords are correct
- Verify PERSONAL_EMAIL is your email

### Step 3: Create Airtable Base (if not done)
Follow SETUP.md from the original system

### Step 4: Run generate.py
```bash
python generate.py
```

---

## 🎯 IMPORTANT NOTES

### Preserve Existing Logic
✅ All existing YouTube scraping logic kept
✅ All existing Claude scoring kept
✅ All existing Airtable operations kept
✅ All existing email sending logic kept
✅ 5-minute delays between emails preserved

### What Changed
✅ Simplified into 2 files instead of 7
✅ Manual execution instead of background scheduler
✅ Personalized follow-ups with Claude (not templates)
✅ Smart reply checking (yesterday only, not all emails)
✅ Consolidated reports (one email instead of multiple)
✅ Instant notifications (know when generation completes)

### What Stayed the Same
✅ config.py structure
✅ airtable_manager.py unchanged
✅ YouTube API usage
✅ Claude scoring (1-10)
✅ Email account rotation
✅ Lead qualification (score 5+/10)

---

## 🐛 TROUBLESHOOTING

### "Claude API error"
→ Check ANTHROPIC_API_KEY in code
→ API uses aicredits.in proxy
→ May have hit rate limits

### "Airtable error"
→ Verify AIRTABLE_BASE_ID in config.py
→ Verify AIRTABLE_API_KEY is correct
→ System auto-retries after 30 seconds

### "No leads found"
→ Try broader niche terms
→ Try "Global" location
→ Increase subscriber range

### "SMTP Authentication Error"
→ Regenerate Gmail app passwords
→ Ensure 2FA is enabled on Gmail
→ Update config.py with new password (keep spaces)

---

## 📊 AIRTABLE FIELDS (No Changes Needed)

Your Airtable base should have these fields (no changes):
- Channel Name (text)
- Email (email)
- Subscriber Count (number)
- Location (text)
- Niche (text)
- YouTube URL (url)
- Status (select: New, Follow-up 1 Sent, Follow-up 2 Sent, Replied, No Response)
- Follow-up Stage (text)
- Date Added (date)
- Last Contact (date)
- Replied (checkbox)
- Reply Date (date)
- Notes (long text)

---

## 💡 USAGE EXAMPLES

### Example 1: Generate 50 Leads
```bash
python generate.py
→ Niche: "Business Coach"
→ Location: "United States"
→ Range: "10,000 - 15,000"
→ Count: 50
→ ✅ Done in ~15 minutes
→ Receive notification email
```

### Example 2: Send Daily Follow-ups
```bash
python followup.py
→ Sends all Day 2 F1 emails
→ Sends all Day 3 F2 emails
→ Checks for yesterday's replies
→ ✅ Done in ~10 minutes
→ Receive consolidated report
```

---

## 🎉 THAT'S IT!

Your system is now:
- ✅ Simpler (2 commands instead of 7 scripts)
- ✅ More powerful (Claude personalization everywhere)
- ✅ Better notifications (consolidated emails)
- ✅ Easier to control (run when you want)
- ✅ More effective (personalized follow-ups)

**Questions?** Check error messages in console output.

**Need help?** Refer back to this guide or SETUP.md.

**Ready to generate leads?**
```bash
python generate.py
```

---

**© Fuelvia System - Refactored & Simplified** 🚀
