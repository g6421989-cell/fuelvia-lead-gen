# 🎯 VISUAL WORKFLOW GUIDE

## Command 1: `python generate.py`

```
┌─────────────────────────────────────────────────────────────┐
│                    LEAD GENERATION FLOW                      │
└─────────────────────────────────────────────────────────────┘

START: python generate.py
  │
  ├─→ 📋 STEP 1: Get User Input
  │    └─ Niche? → Business Coach, Agency Owner, etc.
  │    └─ Location? → USA, UK, Canada, Australia, Global
  │    └─ Subscriber Range? → 1k-5k, 5k-10k, 10k-15k, 15k-20k, 20k+
  │    └─ How many? → 50 (default)
  │
  ├─→ 🔍 STEP 2: YouTube Scraping
  │    └─ Build search query: "Business Coach USA"
  │    └─ Call YouTube API
  │    └─ Get 150+ channel results (to filter down to 50)
  │    └─ Extract: name, subscribers, email, description
  │
  ├─→ 🧠 STEP 3: Claude Analysis (FOR EACH CHANNEL)
  │    ├─ Get last video date
  │    ├─ Send to Claude API:
  │    │   "Score this channel 1-10 based on:
  │    │    - Active (posted in 90 days)?
  │    │    - B2B niche?
  │    │    - Serious business?
  │    │    - Established presence?"
  │    └─ Claude returns: {"score": 7, "reason": "...", "qualified": true}
  │
  ├─→ 🎯 STEP 4: Filter Qualified (Score 5+/10)
  │    └─ Keep only: score >= 5
  │    └─ Discard score < 5
  │    └─ Result: 35 qualified leads
  │
  ├─→ 📧 STEP 5: Send Personalized Emails
  │    ├─ For each qualified lead:
  │    │   ├─ Send to Claude: "Write personal email for {channel_name}"
  │    │   ├─ Claude returns: {"subject": "...", "body": "..."}
  │    │   ├─ Send via Gmail SMTP (rotate between 2 accounts)
  │    │   ├─ Save lead to Airtable
  │    │   └─ Wait 5 minutes before next email (to look natural)
  │    └─ Result: 35 emails sent
  │
  ├─→ 📊 STEP 6: Save to Airtable
  │    ├─ Lead name, email, subscribers, niche, location
  │    ├─ Status: "New"
  │    ├─ Date Added: Today
  │    ├─ Claude Score and reason in Notes
  │    └─ All data searchable and trackable
  │
  └─→ 📨 STEP 7: Send Notification Email
       ├─ To: Your personal email
       ├─ Subject: "✅ Lead Generation Complete - 35 Emails Sent"
       ├─ Content:
       │   - Channels analyzed: 87
       │   - Qualified: 35
       │   - Emails sent: 35
       │   - Timestamp: May 3, 2024 at 2:45 PM
       │   - Next action: "Run followup.py tomorrow"
       └─ Done! ✅

TIME: ~20-30 minutes for 50 leads
```

---

## Command 2: `python followup.py`

```
┌─────────────────────────────────────────────────────────────┐
│              FOLLOW-UP & REPLY CHECKING FLOW                 │
└─────────────────────────────────────────────────────────────┘

START: python followup.py
  │
  ├─→ 📧 STEP 1: Send Follow-up #1 (Day 2 Leads)
  │    ├─ Query Airtable: "Give me leads added YESTERDAY"
  │    ├─ For each lead:
  │    │   ├─ Status must be: "New" (not replied, not F1 sent)
  │    │   ├─ Send to Claude: "Write personalized F1 for {channel_name}"
  │    │   ├─ Claude creates: Subject + Body (unique for each lead)
  │    │   ├─ Send via Gmail SMTP (rotate accounts)
  │    │   ├─ Update Airtable: Status → "Follow-up 1 Sent"
  │    │   └─ Wait 5 minutes
  │    └─ Result: 28 F1 emails sent ✅
  │
  ├─→ 📧 STEP 2: Send Follow-up #2 (Day 3 Leads)
  │    ├─ Query Airtable: "Give me leads added 2 DAYS AGO"
  │    ├─ For each lead:
  │    │   ├─ Status must be: "Follow-up 1 Sent" (not replied)
  │    │   ├─ Send to Claude: "Write personalized F2 for {channel_name}"
  │    │   ├─ Claude creates: Subject + Body (MORE urgent tone)
  │    │   ├─ Send via Gmail SMTP
  │    │   ├─ Update Airtable: Status → "Follow-up 2 Sent"
  │    │   └─ Wait 5 minutes
  │    └─ Result: 15 F2 emails sent ✅
  │
  ├─→ ❌ STEP 3: Mark Day 4+ Leads as "No Response"
  │    ├─ Query Airtable: "Give me leads added 3+ DAYS AGO"
  │    ├─ For each lead:
  │    │   ├─ Check: Haven't replied yet?
  │    │   └─ Update Status → "No Response"
  │    └─ Result: 8 leads marked as no response ❌
  │
  ├─→ 🔍 STEP 4: Check YESTERDAY's Leads for Replies
  │    ├─ Get all leads added YESTERDAY from Airtable
  │    │   └─ Only 45 leads to check (not entire inbox!)
  │    ├─ Connect to Gmail IMAP
  │    ├─ For each yesterday's lead email:
  │    │   ├─ Search Gmail: "Is there a reply FROM this email?"
  │    │   ├─ Check: Subject starts with "Re:" OR has In-Reply-To header
  │    │   ├─ If reply found:
  │    │   │   ├─ Extract: Channel name, email, score, reply time, full message
  │    │   │   ├─ Store in memory
  │    │   │   ├─ Update Airtable: Replied → TRUE
  │    │   │   └─ Print: "🎉 REPLY FOUND from john@example.com"
  │    │   └─ If no reply: skip
  │    └─ Result: 3 replies found 🎉
  │
  ├─→ 📊 STEP 5: Get System Statistics
  │    ├─ Total leads in system: 142
  │    ├─ Total replied: 18 (12.7%)
  │    ├─ Status breakdown:
  │    │   - New: 45
  │    │   - Follow-up 1 Sent: 28
  │    │   - Follow-up 2 Sent: 15
  │    │   - Replied: 18
  │    │   - No Response: 36
  │    └─ Calculate reply rate, pending, etc.
  │
  └─→ 📨 STEP 6: Send ONE Consolidated Report Email
       ├─ To: Your personal email
       ├─ Subject: "📊 Follow-up Complete - 43 Emails Sent, 3 Replies"
       ├─ Content has 3 SECTIONS:
       │
       │   SECTION 1: Today's Follow-ups
       │   ├─ Follow-up #1 sent: 28
       │   ├─ Follow-up #2 sent: 15
       │   ├─ Marked no response: 8
       │   └─ Total sent: 43
       │
       │   SECTION 2: Yesterday's Replies (FULL MESSAGE TEXT)
       │   ├─ REPLY #1
       │   │   Channel: John's Business Tips
       │   │   Email: john@example.com
       │   │   Score: 8/10
       │   │   Replied: May 3, 8:45 AM
       │   │   Message: "Hey Dilip, this sounds perfect..."
       │   │
       │   ├─ REPLY #2
       │   │   Channel: Sarah's Marketing
       │   │   Email: sarah@example.com
       │   │   Score: 9/10
       │   │   Replied: May 3, 9:12 AM
       │   │   Message: "Interested! What's your pricing..."
       │   │
       │   └─ REPLY #3 ...
       │
       │   SECTION 3: Overall System Stats
       │   ├─ Total leads: 142
       │   ├─ Total replied: 18 (12.7%)
       │   ├─ Status breakdown (all statuses)
       │   └─ Summary overview
       │
       └─ Done! ✅

TIME: ~10-20 minutes depending on lead count
```

---

## 📅 COMPLETE WEEKLY TIMELINE

```
┌────────────────────────────────────────────────────────────┐
│                    WEEK TIMELINE                            │
└────────────────────────────────────────────────────────────┘

MONDAY (Day 0)
├─ Run: python generate.py
├─ Input: Business Coach, USA, 10k-15k subscribers, 50 leads
├─ Process: 87 channels analyzed → 35 qualified → 35 emails sent
└─ Output: Notification email ✅
   └─ 35 leads added to Airtable (Status: "New")

TUESDAY (Day 1)
├─ 📧 Leads from Monday reach inboxes
├─ Some start replying (optional - not all will)
└─ Wait and monitor

WEDNESDAY (Day 2)
├─ Run: python followup.py
├─ Process:
│   ├─ Send F1 to Monday's 35 leads (personalized by Claude)
│   ├─ Check Tuesday's leads for replies
│   └─ Mark Monday's leads: Status → "Follow-up 1 Sent"
└─ Output: Consolidated report email showing:
    ├─ F1 sent: 35
    ├─ Replies found (if any)
    └─ System stats
    └─ Airtable updated ✅

THURSDAY (Day 3)
├─ 📧 Follow-up #1 emails reach inboxes
├─ Some new replies coming in
└─ Wait and monitor

FRIDAY (Day 4)
├─ Run: python followup.py (again)
├─ Process:
│   ├─ Send F1 to Wednesday's leads (if new batch added)
│   ├─ Send F2 to Monday's leads (personalized by Claude)
│   ├─ Mark Tuesday's leads: "Follow-up 1 Sent" → "Follow-up 2 Sent"
│   ├─ Check Wednesday's leads for replies
│   └─ If Monday still no reply: Mark as "No Response"
└─ Output: Consolidated report showing:
    ├─ F1 sent: X
    ├─ F2 sent: 35
    ├─ No response: ~5-8
    ├─ New replies from Wednesday
    └─ Updated system stats
    └─ Airtable updated ✅

WEEKEND (Days 5-6)
├─ Optional: Check Gmail for hot leads
├─ Respond personally to replies
├─ Update Airtable manually if needed
└─ Plan next Monday's lead generation

NEXT MONDAY
└─ Start new batch:
   python generate.py
   (Repeat cycle)

ONGOING:
├─ Every time you run followup.py:
│   ├─ F1 emails sent
│   ├─ F2 emails sent  
│   ├─ No response marked
│   ├─ Yesterday's replies checked
│   └─ Consolidated report sent
├─ You get complete visibility
├─ One email per followup run (not 4 different emails)
└─ Full personalization with Claude
```

---

## 🎯 KEY IMPROVEMENTS vs OLD SYSTEM

| Feature | OLD | NEW |
|---------|-----|-----|
| Commands needed | 7 scripts | 2 scripts |
| Background scheduler | Yes (always on) | No (run when you want) |
| Follow-up emails | Generic templates | Claude personalized |
| Notifications | Multiple emails daily | 1 consolidated email |
| Reply checking | All emails checked | Only yesterday's leads |
| Setup complexity | High | Very simple |
| Control | Automated, hard to manage | Manual, full control |
| Laptop requirement | Must stay on 24/7 | Only when running commands |

---

## 🚀 QUICK REFERENCE

### To Generate New Leads:
```bash
python generate.py
```
→ 15-30 min → Get notification email ✅

### To Send Follow-ups & Check Replies:
```bash
python followup.py
```
→ 10-20 min → Get consolidated report email ✅

### To Run Both (Full Cycle):
```bash
python generate.py  # Monday
python followup.py  # Wednesday
python followup.py  # Friday
python followup.py  # Next Monday (checks replies from last leads)
```

---

## 💡 PRO TIPS

1. **Run `followup.py` every morning** at ~9 AM to send follow-ups consistently
2. **Check your email** immediately after notification to see full context
3. **Respond personally to hot leads** quickly (they're most interested right after replying)
4. **Use Airtable as source of truth** - all data synced there
5. **Claude personalization** is your secret weapon - it's what makes replies happen

---

## 📞 NEXT STEPS

1. **Verify setup:** `pip install -r requirements.txt`
2. **Check config.py:** All API keys correct?
3. **First run:** `python generate.py` with 10 test leads
4. **Monitor:** Watch for notification email
5. **Verify:** Check Airtable - are leads there?
6. **Tomorrow:** Run `python followup.py` and see the magic! ✨

---

**Ready to go?** Start with:
```bash
python generate.py
```

You've got this! 🚀
