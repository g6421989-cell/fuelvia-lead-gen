#!/usr/bin/env python3
# ============================================================
# SMTP Connection Test — Hostinger Accounts
# ============================================================
# Tests all 3 email accounts for authentication and sending
# ============================================================

import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def load_config():
    """Load email configuration from JSON."""
    try:
        with open("email_config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return None


def test_smtp_connection(email, password, smtp_server, smtp_port, use_tls=True):
    """Test SMTP connection for a single account."""
    print(f"\n{'='*60}")
    print(f"Testing: {email}")
    print(f"{'='*60}")

    try:
        # Connect to SMTP server
        print(f"  [1/3] Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        print(f"  [OK] Connected to {smtp_server}:{smtp_port}")

        # Start TLS
        if use_tls:
            print(f"  [2/3] Starting TLS encryption...")
            server.starttls()
            print(f"  [OK] TLS encryption enabled")

        # Login
        print(f"  [3/3] Authenticating with credentials...")
        server.login(email, password)
        print(f"  [OK] Authentication successful!")

        # Test send (to self)
        print(f"  [4/4] Testing email send...")
        test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = MIMEMultipart()
        message["From"] = email
        message["To"] = email
        message["Subject"] = f"Fuelvia SMTP Test - {test_time}"

        body = f"""
This is an automated SMTP test from Fuelvia.

Account: {email}
Server: {smtp_server}:{smtp_port}
Time: {test_time}

If you received this, your SMTP account is working correctly.
        """

        message.attach(MIMEText(body, "plain"))
        server.sendmail(email, [email], message.as_string())
        print(f"  [OK] Test email sent to {email}")

        # Close connection
        server.quit()
        print(f"  [OK] Connection closed gracefully")

        print(f"\n[OK] SUCCESS: {email} is working perfectly!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"\n[ERROR] AUTHENTICATION FAILED: {email}")
        print(f"   Error: {str(e)[:200]}")
        print(f"   Check email address and password")
        return False

    except smtplib.SMTPException as e:
        print(f"\n[ERROR] SMTP ERROR: {email}")
        print(f"   Error: {str(e)[:200]}")
        return False

    except Exception as e:
        print(f"\n[ERROR] CONNECTION ERROR: {email}")
        print(f"   Error: {str(e)[:200]}")
        return False


def main():
    """Test all email accounts."""
    print("\n" + "="*60)
    print("  FUELVIA — HOSTINGER SMTP TEST")
    print("="*60)

    config = load_config()
    if not config:
        print("Cannot proceed without config file")
        sys.exit(1)

    accounts = config.get("outreach_emails", [])
    if not accounts:
        print("No outreach emails configured")
        sys.exit(1)

    print(f"\nFound {len(accounts)} accounts to test:")
    for acc in accounts:
        print(f"  • {acc['email']}")

    results = {}
    for account in accounts:
        email = account["email"]
        password = account["password"]
        smtp_server = account["smtp_server"]
        smtp_port = account["smtp_port"]
        use_tls = account.get("use_tls", True)

        results[email] = test_smtp_connection(email, password, smtp_server, smtp_port, use_tls)

    # Summary
    print(f"\n\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for email, success in results.items():
        status = "[OK] PASS" if success else "[ERROR] FAIL"
        print(f"  {status}  {email}")

    print(f"\nResult: {passed}/{total} accounts working")

    if passed == total:
        print(f"\n[DONE] All {total} accounts are configured correctly and ready to use!")
        return 0
    else:
        print(f"\n[WARN]  {total - passed} account(s) need attention. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
