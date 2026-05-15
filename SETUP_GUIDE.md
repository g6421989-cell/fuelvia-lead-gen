# ============================================================
# FUELVIA SYSTEM - COMPLETE SETUP GUIDE
# ============================================================

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
# Install Python requirements
pip install -r requirements.txt

# Or if using pip3
pip3 install -r requirements.txt
```

### Step 2: Configure .env File

```bash
# Copy example to actual .env (if not already done)
cp .env.example .env

# OR manually create .env with your credentials
# See section below for what goes in .env
```

### Step 3: Validate Configuration

```bash
python config_secure.py
```

Expected output:
```
✅ Configuration validated successfully
```

---

## 📝 Detailed Setup

### Part 1: Generate & Protect Your Secrets

#### What is `.env`?

The `.env` file contains all your sensitive information:
- YouTube API keys
- Notion database credentials
- Email account passwords
- Claude API key

**⚠️ IMPORTANT:** Never commit `.env` to git!

#### Create .env File

Create file: `new lead system/.env`

Copy this and fill in YOUR values:

```env
# YouTube API Keys (get from Google Cloud Console)
YOUTUBE_API_KEY_1=your_key_1_here
YOUTUBE_API_KEY_2=your_key_2_here
YOUTUBE_API_KEY_3=your_key_3_here
YOUTUBE_API_KEY_4=your_key_4_here

# Notion (from Notion integrations)
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_database_id_here

# Claude API (from aicredits.in)
CLAUDE_API_KEY=your_claude_api_key_here

# Email Account 1
OUTREACH_EMAIL_1=fuelvia.co@gmail.com
OUTREACH_PASSWORD_1=your_app_password_here

# Email Account 2
OUTREACH_EMAIL_2=fuelviasubscriptions@gmail.com
OUTREACH_PASSWORD_2=your_app_password_here

# Email Account 3
OUTREACH_EMAIL_3=fuelvia.co01@gmail.com
OUTREACH_PASSWORD_3=your_app_password_here

# Reporting Email
REPORTING_EMAIL=Fuelviaa01@gmail.com
REPORTING_PASSWORD=your_app_password_here

# Other settings
EMAIL_ROTATION_DELAY=60
CALENDAR_LINK=https://calendly.com/your-link
SENDER_NAME=Your Name
SENDER_TITLE=Your Title
COMPANY_NAME=Your Company
```

#### Update .gitignore

The `.gitignore` file should already have:

```
.env
.env.local
config.local.py
logs/
backups/
```

**Check:** Run `git status`
- You should NOT see `.env` listed
- If you see it, run: `git rm --cached .env`

---

### Part 2: Email Account Setup

#### Gmail App Passwords

For each Gmail account, create an "App Password":

1. Go to myaccount.google.com
2. Click "Security" (left menu)
3. Enable "2-Step Verification" (if not enabled)
4. Go back to Security
5. Find "App passwords" (bottom)
6. Select: Mail + Windows Computer
7. Copy the 16-character password
8. Paste into `.env`

⚠️ **Do NOT use your regular Gmail password!**

---

### Part 3: New File Structure

Your project should now look like:

```
new lead system/
├── .env                      ← SECRETS (git-ignored)
├── .gitignore              ← Tells git to ignore .env
├── config_secure.py        ← NEW: Loads from .env
├── error_logger.py         ← NEW: Error tracking
├── backup_manager.py       ← NEW: Data backup
├── email_compliance.py     ← NEW: Unsubscribe + GDPR
├── notion_manager.py       ← Updated to use backup
├── followup.py             ← Updated to use error logger
├── generate.py             ← Updated to use error logger
├── claude_helpers.py
├── email_helpers.py
├── youtube_enricher.py
├── channel_qualifier.py
├── logs/                    ← NEW: Error logs
│   ├── system.log
│   └── errors.log
├── backups/                 ← NEW: Data backups
│   └── leads_backup_*.db
├── leads_backup.db         ← SQLite backup database
├── compliance.db           ← Compliance tracking database
└── requirements.txt        ← Updated dependencies
```

---

## 🔒 Security Checklist

Before deploying to client, verify:

- [ ] `.env` file created with all secrets
- [ ] `.gitignore` includes `.env`
- [ ] Run `python config_secure.py` passes validation
- [ ] No API keys in any Python files (except config_secure.py)
- [ ] Gmail app passwords used (not regular passwords)
- [ ] YouTube API quota requested (higher than 10,000)
- [ ] Notion API key with correct database access
- [ ] `logs/` directory exists and is writable
- [ ] `backups/` directory exists and is writable
- [ ] Error logging working (check logs/system.log)

---

## 📊 New Features

### 1. Error Logging

All errors are now logged to `logs/errors.log`

Check logs:
```bash
tail -f logs/system.log          # Real-time log
cat logs/errors.log               # Error log only
```

### 2. Automatic Backups

SQLite backup database automatically created:

```
leads_backup.db                   ← Main backup
backups/leads_backup_*.db         ← Daily backups
```

Check backup status:
```python
from backup_manager import backup_manager
stats = backup_manager.get_backup_stats()
print(stats)
```

### 3. Email Compliance

Unsubscribe links and privacy footer added to all emails

Check compliance:
```python
from email_compliance import compliance
report = compliance.get_compliance_report()
print(report)
```

### 4. Error Alerts

Critical errors send alert email to admin

Configure in `.env`:
```
ALERT_EMAIL=your_email@example.com
ALERT_ON_ERROR=true
```

---

## 🧪 Testing

### Test 1: Validate Config

```bash
python config_secure.py
```

Expected: ✅ Configuration validated successfully

### Test 2: Check Logging

```bash
python -c "from error_logger import logger; logger.log_success('Test message')"
cat logs/system.log
```

Expected: Message appears in logs/system.log

### Test 3: Test Backup

```bash
python -c "from backup_manager import backup_manager; backup_manager.create_full_backup()"
ls -la backups/
```

Expected: Backup file created in backups/ directory

### Test 4: Test Compliance

```bash
python -c "from email_compliance import compliance; print(compliance.get_compliance_report())"
```

Expected: Compliance stats printed

---

## 🚨 Troubleshooting

### Error: "No module named 'dotenv'"

Solution:
```bash
pip install python-dotenv
```

### Error: ".env file not found"

Solution: Create .env file in the same directory as config_secure.py

### Error: "Could not connect to Notion"

Check:
- NOTION_API_KEY is correct
- NOTION_DATABASE_ID is correct
- API key has access to database

### Error: "Gmail authentication failed"

Check:
- Using App Password (not regular Gmail password)
- 2-Step Verification is enabled
- Password is exactly correct (16 characters)

### Error: "logs directory not writable"

Solution:
```bash
mkdir -p logs
chmod 755 logs
```

---

## 📈 Monitoring

### Daily Checks

```bash
# Check system log
tail -50 logs/system.log

# Check error log
cat logs/errors.log | tail -20

# Check backup status
ls -lh backups/

# Verify backup database
python -c "from backup_manager import backup_manager; print(backup_manager.get_backup_stats())"
```

### Weekly Maintenance

```bash
# Cleanup old backups (automatic, but verify)
python -c "from backup_manager import backup_manager; backup_manager.cleanup_old_backups(days=30)"

# Clear old logs
python -c "from error_logger import logger; logger.clear_old_logs(days=30)"
```

---

## 🔄 Running the System

### Generate Leads

```bash
python generate.py
```

Uses:
- config_secure.py (for API keys)
- error_logger.py (for logging)
- backup_manager.py (for backups)
- email_compliance.py (for unsubscribe links)

### Run Follow-ups

```bash
python followup.py
```

Same enhanced features + error alerts

---

## 📋 Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| YOUTUBE_API_KEY_1-4 | YouTube API keys | AIzaSy... |
| NOTION_API_KEY | Notion integration | ntn_... |
| NOTION_DATABASE_ID | Notion database ID | aa9bd99d-... |
| CLAUDE_API_KEY | Claude API key | sk-live-... |
| OUTREACH_EMAIL_1-3 | Gmail accounts | email@gmail.com |
| OUTREACH_PASSWORD_1-3 | App passwords | 16-char password |
| REPORTING_EMAIL | Admin email | admin@company.com |
| EMAIL_ROTATION_DELAY | Wait between emails | 60 (seconds) |
| LOG_FILE | System log location | logs/system.log |
| ALERT_EMAIL | Alert recipient | admin@company.com |
| ENVIRONMENT | dev/staging/prod | production |

---

## ✅ Deployment Checklist

Before giving to client:

- [ ] .env created and populated
- [ ] .gitignore configured
- [ ] All validations pass
- [ ] Test logging works
- [ ] Test backup works
- [ ] Test compliance works
- [ ] Test error alerts work
- [ ] Old logs and backups cleaned up
- [ ] logs/ directory exists
- [ ] backups/ directory exists
- [ ] requirements.txt installed
- [ ] YouTube API quota requested
- [ ] Notion API access verified
- [ ] Gmail app passwords created
- [ ] Privacy policy URL set
- [ ] Unsubscribe mechanism working

---

## 🆘 Support

If something breaks:

1. Check logs/errors.log for errors
2. Run: `python config_secure.py` to validate config
3. Check system has write permissions to logs/ and backups/
4. Verify .env file is in correct location
5. Check error alert email for notifications

---

**Setup Complete!** Your Fuelvia system is now secure, monitored, and backed up. 🎉
