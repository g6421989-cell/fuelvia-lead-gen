# Fuelvia Email Workflow - Quick Start Guide

## What You Can Do Now

You now have a complete email campaign system with 3 major features:

### 1. ✉️ Send Emails to New Leads
**Location:** Overview tab → "Email Campaign Actions" card → "Send Emails to New Leads" button

**What it does:**
- Finds all leads with Status = "New"
- Sends personalized cold emails
- Rotates through your 3 Gmail accounts
- Saves which account sent each email
- Updates lead status to "Contacted"

**Example:**
```
You have 10 leads with Status="New"
Click "Send Emails" → System sends 10 cold emails from rotating accounts
After completion → All 10 leads now have Status="Contacted"
```

---

### 2. ↩️ Send Follow-ups
**Location:** Overview tab → "Email Campaign Actions" card → "Send Follow-ups" button

**What it does:**
- Finds all leads with Status = "Contacted"
- Sends follow-up emails from the SAME account that sent the cold email
- Updates lead status to "Follow-up Sent"
- Enforces 2-email maximum policy

**Example:**
```
Day 0: Send cold emails from Account A, B, C (rotated)
Lead 1: Account A, Status → "Contacted"
Lead 2: Account B, Status → "Contacted"

Day 2: Click "Send Follow-ups"
Lead 1: Follow-up from Account A (same!), Status → "Follow-up Sent"
Lead 2: Follow-up from Account B (same!), Status → "Follow-up Sent"

Day 3+: No more emails sent (2 email max policy enforced)
```

---

### 3. 💬 Check for Replies
**Location:** 
- Overview tab → "Email Campaign Actions" card → "Check for Replies" button
- OR Replies tab → "Check for New Replies" button

**What it does:**
- Scans all 3 email accounts for replies
- Matches replies to your leads
- Updates Notion status to "Replied"
- Shows all replies in Replies Dashboard

**Example:**
```
You've sent 10 cold emails + 10 follow-ups
2 leads reply to your emails
Click "Check Replies" → System finds 2 replies
→ Notion updates those leads to Status="Replied"
→ Replies Dashboard shows 2 new replies with messages
```

---

## How to Use (Step by Step)

### Step 1: Add Leads
1. Go to "Scraper" tab
2. Select your criteria (niche, location, subscriber range)
3. Click "Start Scraping"
4. Wait for leads to be added with Status = "New"

### Step 2: Send Cold Emails
1. Go to "Overview" tab
2. Click "Send Emails to New Leads" button
3. Confirm the popup
4. Wait for completion message
5. Go to "All Leads" tab
6. Verify Status changed from "New" → "Contacted"

### Step 3: Wait 48 Hours (or just do it immediately for testing)
The system is designed to:
- Send cold emails on Day 0
- Send follow-ups on Day 2
- Check for replies starting Day 1

For testing, you can trigger immediately.

### Step 4: Send Follow-ups
1. Go to "Overview" tab
2. Click "Send Follow-ups" button
3. Confirm the popup
4. Wait for completion
5. Verify Status changed from "Contacted" → "Follow-up Sent"

### Step 5: Check for Replies
1. Go to "Overview" tab OR "Replies" tab
2. Click "Check for Replies" button
3. System scans your 3 email accounts
4. Any replies are added to "Replies" dashboard
5. Leads with replies get Status = "Replied"

---

## Dashboard Overview

### Overview Tab
- **Stat Cards:** Shows total leads, emails sent, replies received
- **Email Campaign Actions Card:** The 3 main buttons to control campaigns
- **Campaign Activity:** Shows weekly stats and response rates

### All Leads Tab
- View all leads with their status
- Statuses: New, Contacted, Follow-up Sent, Replied, Closed

### Emails Tab
- See all emails sent from your 3 accounts
- Shows from/to addresses and send dates

### Replies Tab
- **Check for New Replies button:** Manually scan for replies
- **Replies Table:** Shows all received replies with:
  - Channel Name
  - Email address
  - Status (Replied)
  - Reply Date
  - Message Preview

---

## Status Transitions (2-Email Policy)

```
New 
  ↓ (after "Send Emails")
Contacted
  ↓ (after "Send Follow-ups")
Follow-up Sent
  ↓ (if reply detected)
Replied
  
OR if no reply after follow-up:
Follow-up Sent
  ↓ (after 48+ hours)
Closed (no more emails sent)
```

---

## Important Notes

1. **Account Rotation:** Cold emails rotate through your 3 accounts
   - Lead 1: Account A
   - Lead 2: Account B
   - Lead 3: Account C
   - Lead 4: Account A (cycles)

2. **Same Account for Follow-up:** Each follow-up comes from the SAME account as the cold email
   - If cold email from Account A → follow-up from Account A
   - If cold email from Account B → follow-up from Account B

3. **2-Email Maximum:** Each lead receives exactly 2 emails maximum
   - Cold email (Day 0)
   - Follow-up (Day 2)
   - No 3rd email, even if no reply

4. **Automatic Reply Detection:** System auto-detects replies and updates status
   - Just click "Check for Replies" to scan
   - No manual status updates needed

---

## Common Questions

**Q: Why is the follow-up from the same account?**
A: Better deliverability and reply rates. Leads recognize the same sender.

**Q: What if I want to send more than 2 emails?**
A: The system is locked to 2-email maximum policy to comply with email best practices and avoid spam complaints.

**Q: Can I manually check for replies?**
A: Yes! Click "Check for Replies" anytime. The system scans all 3 accounts for new responses.

**Q: What happens to leads that reply?**
A: They get Status="Replied" and appear in the Replies Dashboard with their message.

**Q: What happens to leads with no replies?**
A: After follow-up is sent (Day 2), if no reply by Day 3+, they become Status="Closed" and receive no more emails.

---

## API Endpoints (For Developers)

If you're integrating with other systems:

- **POST /api/send-emails** - Send to all "New" leads
- **POST /api/send-followup** - Send to all "Contacted" leads  
- **POST /api/check-replies** - Scan accounts for replies
- **GET /api/replies** - Get all leads with replies

---

## Support

If something goes wrong:
1. Check the browser console (F12) for errors
2. Check /api/logs for server-side errors
3. Verify Notion database is connected
4. Verify email accounts have proper credentials

All operations run in background threads, so you won't see delays in the UI.

---

**Status:** ✅ Ready to Use
**Next Step:** Go to Scraper tab and add some leads!
