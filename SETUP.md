# Fuelvia Lead Generation System — Setup Guide

## Prerequisites
- Python 3.8+
- VS Code (recommended)
- Airtable account (free tier works)
- Two Gmail accounts with App Passwords enabled

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2: Create Airtable Base

1. Log in at [airtable.com](https://airtable.com)
2. Click **+ Add a base** → Start from scratch → Name it "Fuelvia"
3. Rename the default table to **Leads**
4. Add these fields exactly:

| Field Name | Field Type |
|---|---|
| Channel Name | Single line text |
| Email | Email |
| Subscriber Count | Number |
| Location | Single line text |
| Niche | Single line text |
| YouTube URL | URL |
| Status | Single select (options: New, Follow-up 1 Sent, Follow-up 2 Sent, Replied, No Response) |
| Follow-up Stage | Single line text |
| Date Added | Date |
| Last Contact | Date |
| Open Rate | Number |
| Replied | Checkbox |
| Reply Date | Date |
| Notes | Long text |

---

## Step 3: Get Your Airtable Base ID

1. Open your Airtable base
2. Look at the URL: `https://airtable.com/appXXXXXXXXXXXXXX/tblYYYYY/...`
3. Copy the `appXXXXXXXXXXXXXX` part — that's your Base ID

---

## Step 4: Update config.py

Open `config.py` and update:

```python
AIRTABLE_BASE_ID = "appYOURACTUALBASEIDHERE"
CALENDAR_LINK = "https://calendly.com/your-actual-link"
```

---

## Step 5: Gmail App Passwords

For each Gmail account:
1. Go to **Google Account → Security → 2-Step Verification** (must be enabled)
2. Scroll to **App Passwords**
3. Select "Mail" and "Windows Computer"
4. Copy the 16-character password
5. Update `config.py` with the new password (keep the spaces)

---

## Step 6: Run the System

```bash
python start.py
```

---

## Usage

### Generate Leads (Manual)
```bash
python lead_generator.py
```
Fill in the form → system scrapes YouTube → sends emails → logs to Airtable.

### Full Automation (24/7)
```bash
python scheduler.py
```
Leave running. It will:
- Send follow-ups every morning at 9:00 AM
- Monitor replies every 5 minutes
- Send daily report at 5:00 PM

### Individual Scripts
```bash
python followup_system.py   # Run follow-ups now
python reply_monitor.py     # Monitor replies now
python daily_reporter.py    # Send report now
```

---

## Troubleshooting

**"AIRTABLE_BASE_ID not set"** → Update `AIRTABLE_BASE_ID` in config.py

**SMTP Authentication Error** → Regenerate Gmail App Password; ensure 2FA is enabled

**YouTube Quota Exceeded** → Free quota is 10,000 units/day. Wait 24 hours for reset.

**No leads found** → Try broader niche terms or "Global" location. Some niches have fewer channels with emails in descriptions.

**Duplicate notifications** → Notified set resets when monitor restarts. This is normal on first run.

---

## Architecture

```
start.py              → Menu launcher
lead_generator.py     → YouTube scraping + initial outreach
followup_system.py    → Day 2 & 3 automated follow-ups
reply_monitor.py      → Continuous inbox monitoring
daily_reporter.py     → 5 PM daily report
scheduler.py          → Background orchestrator (runs all above)
airtable_manager.py   → All Airtable CRUD operations
email_templates.py    → Email copy and personalization
config.py             → All credentials and settings
```
