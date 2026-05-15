# ============================================================
# EMAIL COMPLIANCE - Unsubscribe, Privacy, GDPR
# ============================================================

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from error_logger import logger


class EmailCompliance:
    def __init__(self):
        self.db_file = "compliance.db"
        self.init_compliance_database()

    def init_compliance_database(self):
        """Initialize compliance database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Unsubscribed emails table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS unsubscribed_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                reason TEXT,
                unsubscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Bounced emails table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bounced_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                bounce_type TEXT,
                bounce_reason TEXT,
                bounced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Consent table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS consent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                consent_type TEXT,
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            conn.commit()
            conn.close()

            logger.log_success("Compliance database initialized")

        except Exception as e:
            logger.log_error(f"Failed to initialize compliance database: {str(e)}")

    def add_unsubscribe_footer(self, email_body, email_address, client_id="default"):
        """Add unsubscribe link and privacy footer to email"""

        # Generate unsubscribe token
        token = self.generate_unsubscribe_token(email_address)

        unsubscribe_link = f"https://fuelvia.app/unsubscribe?token={token}&email={email_address}"
        privacy_link = "https://fuelvia.app/privacy"
        terms_link = "https://fuelvia.app/terms"

        footer = f"""

───────────────────────────────────────
This email is sent to {email_address} from Fuelvia System.

If you would like to unsubscribe from our emails:
[Unsubscribe]({unsubscribe_link})

Need to know more? Read our:
- Privacy Policy: {privacy_link}
- Terms of Service: {terms_link}

For support, reply to this email.
© Fuelvia {datetime.now().year}
───────────────────────────────────────"""

        return email_body + footer

    def generate_unsubscribe_token(self, email_address):
        """Generate secure unsubscribe token"""
        data = f"{email_address}:{datetime.now().date()}"
        token = hashlib.sha256(data.encode()).hexdigest()[:32]
        return token

    def process_unsubscribe(self, email_address, token, reason="user_request"):
        """Process unsubscribe request"""
        try:
            # Verify token
            if not self.verify_unsubscribe_token(email_address, token):
                logger.log_warning(f"Invalid unsubscribe token for {email_address}")
                return False

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Check if already unsubscribed
            cursor.execute('SELECT * FROM unsubscribed_emails WHERE email=?', (email_address,))
            if cursor.fetchone():
                conn.close()
                logger.log_info(f"Already unsubscribed: {email_address}")
                return True

            # Add to unsubscribed list
            cursor.execute(
                'INSERT INTO unsubscribed_emails (email, reason) VALUES (?, ?)',
                (email_address, reason)
            )

            conn.commit()
            conn.close()

            logger.log_success(f"Unsubscribed: {email_address}")
            return True

        except Exception as e:
            logger.log_error(f"Failed to process unsubscribe: {str(e)}")
            return False

    def verify_unsubscribe_token(self, email_address, token):
        """Verify unsubscribe token is valid"""
        expected_token = self.generate_unsubscribe_token(email_address)
        return token == expected_token

    def is_unsubscribed(self, email_address):
        """Check if email is unsubscribed"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM unsubscribed_emails WHERE email=?', (email_address,))
            result = cursor.fetchone()
            conn.close()

            return result is not None

        except Exception as e:
            logger.log_error(f"Failed to check unsubscribe status: {str(e)}")
            return False

    def log_bounce(self, email_address, bounce_type="unknown", reason=""):
        """Log bounced email"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO bounced_emails (email, bounce_type, bounce_reason) VALUES (?, ?, ?)',
                (email_address, bounce_type, reason)
            )

            conn.commit()
            conn.close()

            logger.log_warning(f"Bounce logged: {email_address} ({bounce_type})")

        except Exception as e:
            logger.log_error(f"Failed to log bounce: {str(e)}")

    def is_hard_bounce(self, email_address):
        """Check if email is hard bounce (invalid)"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM bounced_emails WHERE email=? AND bounce_type=?',
                (email_address, 'hard')
            )
            result = cursor.fetchone()
            conn.close()

            return result is not None

        except Exception as e:
            logger.log_error(f"Failed to check bounce status: {str(e)}")
            return False

    def log_consent(self, email_address, consent_type="email_marketing", status="opted_in"):
        """Log consent record for GDPR compliance"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO consent_logs (email, consent_type, status) VALUES (?, ?, ?)',
                (email_address, consent_type, status)
            )

            conn.commit()
            conn.close()

            logger.log_info(f"Consent logged: {email_address} - {status}")

        except Exception as e:
            logger.log_error(f"Failed to log consent: {str(e)}")

    def get_privacy_policy_html(self):
        """Return privacy policy HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fuelvia Privacy Policy</title>
        </head>
        <body>
            <h1>Fuelvia Privacy Policy</h1>

            <h2>Data Collection</h2>
            <p>We collect email addresses and channel information from YouTube creators for outreach purposes.</p>

            <h2>Data Usage</h2>
            <p>Your data is used to:</p>
            <ul>
                <li>Send personalized outreach emails</li>
                <li>Track engagement and replies</li>
                <li>Improve our system</li>
            </ul>

            <h2>Data Protection</h2>
            <p>We protect your data with industry-standard security measures.</p>

            <h2>Your Rights</h2>
            <ul>
                <li>Unsubscribe from emails anytime</li>
                <li>Request data deletion</li>
                <li>Access your data</li>
            </ul>

            <h2>Contact</h2>
            <p>For privacy questions: privacy@fuelvia.com</p>

            <p>Last updated: {datetime.now().strftime('%Y-%m-%d')}</p>
        </body>
        </html>
        """

    def get_compliance_report(self):
        """Generate compliance report"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM unsubscribed_emails')
            unsubscribed = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM bounced_emails')
            bounced = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM consent_logs WHERE status="opted_in"')
            opted_in = cursor.fetchone()[0]

            conn.close()

            return {
                "unsubscribed": unsubscribed,
                "bounced": bounced,
                "opted_in": opted_in,
            }

        except Exception as e:
            logger.log_error(f"Failed to generate compliance report: {str(e)}")
            return {}


# Global compliance manager
compliance = EmailCompliance()
