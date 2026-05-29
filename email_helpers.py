# ============================================================
# EMAIL HELPERS - Account Rotation & Sending (FIXED)
# ============================================================
# FIX 1: Global EmailRotator instance (maintains state across calls)
# FIX 2: Follow-ups always use original account (never rotate)
# FIX 3: 2-email max per lead (cold + 1 follow-up only)
# ============================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
from email.utils import parseaddr
from datetime import datetime

from config_secure import (
    OUTREACH_ACCOUNTS, REPORTING_ACCOUNT,
    SENDER_NAME, COMPANY_NAME
)


class EmailRotator:
    """Manages outreach email account rotation"""
    def __init__(self):
        self.account_index = 0

    def get_next_account(self):
        """Get next outreach account and rotate"""
        account = OUTREACH_ACCOUNTS[self.account_index % len(OUTREACH_ACCOUNTS)]
        self.account_index += 1
        return account

    def reset_rotation(self):
        """Reset rotation (for testing)"""
        self.account_index = 0


# ============================================================
# FIX 1: GLOBAL INSTANCE - Single rotator for all calls
# ============================================================
global_email_rotator = EmailRotator()


def send_outreach_email(to_email, subject, body, account=None, is_followup=False):
    """
    Send email from outreach account

    - For cold emails: rotates through accounts using global rotator
    - For follow-ups: MUST use provided account (Email Sent From field from Notion)

    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body
        account: Account dict with 'email', 'password', 'smtp_server', 'smtp_port'
        is_followup: True if this is a follow-up email

    Returns:
        (success: bool, sender_email: str or None)
    """
    if not account:
        if is_followup:
            raise ValueError("[ERROR] Follow-up emails MUST specify the original account from 'Email Sent From' field")
        # FIX 1: Use global rotator instead of creating new instance
        account = global_email_rotator.get_next_account()

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} - {COMPANY_NAME} <{account['email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Try multiple ports for Render/cloud environment compatibility
    ports_to_try = [account["smtp_port"], 465, 587, 25]

    for attempt, port in enumerate(ports_to_try, 1):
        try:
            with smtplib.SMTP(account["smtp_server"], port, timeout=30) as server:
                if port != 25:  # Port 25 doesn't use TLS
                    server.starttls()
                server.login(account["email"], account["password"])
                server.sendmail(account["email"], to_email, msg.as_string())
            return True, account["email"]
        except Exception as e:
            error_msg = str(e)[:150]
            if attempt == len(ports_to_try):  # Last attempt
                print(f"  [!!] SMTP failed (all ports): {error_msg}")
                return False, error_msg
            continue

    return False, "All SMTP ports failed"


def send_report_email(to_email, subject, body):
    """Send report from reporting account ONLY"""
    account = REPORTING_ACCOUNT

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} - {COMPANY_NAME} <{account['email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Try multiple ports for Render/cloud environment compatibility
    ports_to_try = [account["smtp_port"], 465, 587, 25]

    for attempt, port in enumerate(ports_to_try, 1):
        try:
            with smtplib.SMTP(account["smtp_server"], port, timeout=30) as server:
                if port != 25:  # Port 25 doesn't use TLS
                    server.starttls()
                server.login(account["email"], account["password"])
                server.sendmail(account["email"], to_email, msg.as_string())
            return True
        except Exception as e:
            error_msg = str(e)[:150]
            if attempt == len(ports_to_try):  # Last attempt
                print(f"  [!!] Report email error (all ports): {error_msg}")
                return False
            continue

    return False


class ReplyChecker:
    """Check for replies from leads in outreach accounts"""

    def connect_imap(self, account):
        """Connect to Gmail IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(account["imap_server"])
            mail.login(account["email"], account["password"])
            return mail
        except Exception as e:
            print(f"  ❌ IMAP connection failed for {account['email']}: {e}")
            return None

    def get_email_body(self, msg):
        """Extract email body"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                pass
        return body

    def is_reply(self, msg):
        """Check if email is a reply"""
        subject = msg.get("Subject", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")
        return (
            subject.lower().startswith("re:") or
            bool(in_reply_to) or
            bool(references)
        )

    def check_for_replies(self, leads_to_check):
        """
        Check for replies from specific leads
        leads_to_check: list of {"email": "...", "channel_name": "...", ...}
        Returns: list of found replies
        """
        replies_found = []
        emails_to_check = {lead["email"]: lead for lead in leads_to_check}

        # Check all outreach accounts
        for account in OUTREACH_ACCOUNTS:
            mail = self.connect_imap(account)
            if not mail:
                continue

            try:
                mail.select("INBOX")
                _, data = mail.search(None, "ALL")
                email_ids = data[0].split()[-200:]  # Check last 200 emails

                for eid in email_ids:
                    try:
                        _, msg_data = mail.fetch(eid, "(RFC822)")
                        msg = email.message_from_bytes(msg_data[0][1])

                        if not self.is_reply(msg):
                            continue

                        _, from_email = parseaddr(msg.get("From", ""))
                        from_email = from_email.lower()

                        # Check if this email is from one of our leads
                        if from_email in emails_to_check:
                            lead = emails_to_check[from_email]
                            reply_body = self.get_email_body(msg)
                            reply_time = msg.get("Date", "")

                            replies_found.append({
                                "channel_name": lead.get("channel_name", ""),
                                "email": from_email,
                                "score": lead.get("score", "?"),
                                "reply_time": reply_time,
                                "message": reply_body[:1000],  # First 1000 chars
                                "full_message": reply_body,
                                "page_id": lead.get("id", "")
                            })

                            print(f"  🎉 REPLY FOUND: {from_email}")

                    except Exception as e:
                        print(f"  ❌ Error processing email: {e}")

            except Exception as e:
                print(f"  ❌ Error checking {account['email']}: {e}")
            finally:
                try:
                    mail.logout()
                except Exception:
                    pass

        return replies_found
