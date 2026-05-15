# ============================================================
# FUELVIA DASHBOARD - Complete Setup & Usage Guide
# ============================================================

## 🚀 Quick Start

### Step 1: Install Dashboard Dependencies

```bash
pip install Flask==3.0.0 flask-cors==4.0.0
```

Or install all updated requirements:
```bash
pip install -r requirements.txt
```

### Step 2: Start the Dashboard

```bash
python app.py
```

Output:
```
============================================================
FUELVIA DASHBOARD STARTING
============================================================
Access: http://localhost:5000
Password: fuelvia2025
Emails config: email_config.json
============================================================
```

### Step 3: Open in Browser

1. Go to: **http://localhost:5000**
2. Enter password: **fuelvia2025**
3. Done! Dashboard loads

---

## 📊 Dashboard Features

### Tab 1: LEADS
- View all scraped leads
- Search by channel name or email
- Filter by status (New, Contacted, Replied)
- See subscriber count and date added
- Pagination support (20 leads per page)

### Tab 2: EMAILS SENT
- View all emails sent from all 3 outreach accounts
- Shows who sent to whom
- Track delivery status
- Combined view of all 3 email accounts

### Tab 3: REPLIES
- See replies received from leads
- Automated reply detection
- Reply message content
- Reply date/time

### Tab 4: SCRAPER (Real-Time)
- **Live YouTube scraping from browser**
- Configure: Niche, Location, Subscriber Range, Lead Count
- **Real-time progress updates** (doesn't require browser refresh)
- Live activity log showing each lead as it's found
- **Scraping continues in background even if you close browser**
- Pause/Resume scraping anytime
- Stop and restart as needed

**Key Feature:** Close browser = scraping still continues in background!

---

## 🔐 Security & Login

### Default Password
```
fuelvia2025
```

### Change Password (for Client)
Edit `app.py` line ~550:
```python
if password == "fuelvia2025":  # Change this to client's password
    session['logged_in'] = True
```

Change to your client's desired password:
```python
if password == "your-client-password-here":
```

Then restart the server.

---

## ✉️ Email Management

### Where Emails Are Stored
All outreach emails are stored in: `email_config.json`

```json
{
  "outreach_emails": [
    {
      "email": "fuelvia.co@gmail.com",
      "password": "bafv dvme pduz nwgi",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587
    },
    ... more emails
  ],
  "reporting_email": {
    "email": "Fuelviaa01@gmail.com",
    "password": "hwwe yhel nmns ofwo",
    ...
  }
}
```

### Change Outreach Emails (for Client)

**When your client provides their company emails, follow these steps:**

1. **Open `email_config.json`**
2. **Replace the outreach emails:**

**Before (Fuelvia emails):**
```json
{
  "email": "fuelvia.co@gmail.com",
  "password": "bafv dvme pduz nwgi",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587
}
```

**After (Client's emails):**
```json
{
  "email": "support@clientcompany.com",
  "password": "client-app-password-here",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587
}
```

3. **For Gmail accounts:** Use Gmail App Passwords, NOT regular passwords
   - Go to myaccount.google.com
   - Security → App passwords
   - Select "Mail" and "Windows Computer"
   - Copy 16-character password into email_config.json

4. **Restart the server:**
```bash
# Stop current server (Ctrl+C)
# Start again:
python app.py
```

5. **New emails will be used for next scrapes!**

### Reporting Email (Stays Same)
- `reporting_email` is for alerts and reports
- Usually stays the same (your email)
- Can be changed same way as outreach emails if needed

### Example: Switch to Client's 3 Company Emails

```json
{
  "outreach_emails": [
    {
      "email": "john@acmecorp.com",
      "password": "xxxx xxxx xxxx xxxx",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587
    },
    {
      "email": "sarah@acmecorp.com",
      "password": "yyyy yyyy yyyy yyyy",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587
    },
    {
      "email": "mike@acmecorp.com",
      "password": "zzzz zzzz zzzz zzzz",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587
    }
  ],
  "reporting_email": {
    "email": "reports@acmecorp.com",
    "password": "wwww wwww wwww wwww",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
  }
}
```

---

## 🎯 How Client Uses Dashboard

### For End Client (What They See):

1. **Open browser:** `http://your-domain.com:5000`
2. **Enter password**
3. **Choose action:**
   - View all leads scraped so far
   - View emails sent and replies
   - Click "Scraper" tab and start live scraping
   - Real-time progress updates
   - Scraping works even if they close browser

### What They CAN'T Do:
- ❌ See any code
- ❌ Change configuration
- ❌ Access backend directly
- ❌ Modify system files
- ✅ Only see dashboard

### What They CAN Do:
- ✅ View all leads
- ✅ Start/pause/stop scraping
- ✅ See real-time progress
- ✅ View emails and replies
- ✅ Download/screenshot data

---

## 🌐 Deployment to DigitalOcean

### Step 1: Create VPS
- Go to DigitalOcean
- Create "Droplet" (basic $6/month)
- Ubuntu 22.04 LTS

### Step 2: Upload Code
```bash
scp -r ./new\ lead\ system/ root@your-ip:/root/fuelvia
```

### Step 3: Install & Run
```bash
ssh root@your-ip
cd /root/fuelvia
pip install -r requirements.txt
python app.py &
```

### Step 4: Access Remotely
Browser: `http://your-ip:5000`

### Step 5: Keep Running (Systemd Service)
Create `/etc/systemd/system/fuelvia.service`:
```ini
[Unit]
Description=Fuelvia Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/fuelvia
ExecStart=/usr/bin/python3 /root/fuelvia/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
systemctl start fuelvia
systemctl enable fuelvia
```

---

## 📋 File Structure

```
new lead system/
├── app.py                      ← Dashboard backend (Flask)
├── templates/
│   └── dashboard.html          ← Dashboard frontend
├── email_config.json           ← Email configuration (EASY TO CHANGE)
├── config_secure.py            ← Main configuration
├── generate.py                 ← Lead scraping (called by app.py)
├── notion_manager.py           ← Notion integration
├── email_helpers.py            ← Email system
├── backup_manager.py           ← SQLite backup
├── error_logger.py             ← Error logging
├── requirements.txt            ← Dependencies (updated with Flask)
└── logs/
    └── system.log              ← System logs
```

---

## 🔧 Troubleshooting

### Port 5000 Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Login Not Working
- Check password in `app.py` (default: `fuelvia2025`)
- Check if Flask is running
- Clear browser cookies

### Scraping Not Starting
1. Check YouTube API quota
2. Check Notion API key in .env
3. Check logs in `logs/system.log`

### Emails Not Sending
1. Check email_config.json
2. Verify passwords are Gmail App Passwords (not regular passwords)
3. Check if SMTP port 587 is open

### Can't Connect to Server
1. Check if app.py is running: `ps aux | grep app.py`
2. Check firewall: Allow port 5000
3. Check logs

---

## 📝 Change Log

### Dashboard v1.0
- ✅ Real-time lead scraping
- ✅ 4 main tabs (Leads, Emails, Replies, Scraper)
- ✅ Background job support
- ✅ Easy email configuration
- ✅ Live progress updates
- ✅ Works even if browser closes
- ✅ Simple password login

---

## 🎓 For Your Client

### How to Change Email Addresses

**You (Admin) will:**
1. Open `email_config.json` in text editor
2. Replace old email addresses with new ones
3. Get Gmail App Passwords from client
4. Paste into config file
5. Restart server

**Client (End User) will:**
1. Refresh dashboard in browser
2. Start scraping with new emails
3. Everything else works the same

---

## ✨ Key Features Summary

| Feature | Status |
|---------|--------|
| Real-time scraping | ✅ Works |
| Background jobs | ✅ Works |
| Pause/Resume | ✅ Works |
| Browser close = continues | ✅ Works |
| Easy email change | ✅ Works |
| Live logs | ✅ Works |
| Password protected | ✅ Works |
| 4 tabs dashboard | ✅ Works |
| Mobile responsive | ✅ Works |
| No code visible | ✅ Works |

---

**Dashboard is production-ready!** 🚀
