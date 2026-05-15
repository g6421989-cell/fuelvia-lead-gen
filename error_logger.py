# ============================================================
# ERROR LOGGER - Comprehensive error tracking & alerts
# ============================================================

import logging
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

class ErrorLogger:
    def __init__(self):
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)

        # Setup logging
        self.log_file = "logs/system.log"
        self.error_file = "logs/errors.log"

        # Configure logger
        self.logger = logging.getLogger("FuelviaSystem")
        self.logger.setLevel(logging.INFO)

        # File handler for all logs (UTF-8 for emojis)
        fh_all = logging.FileHandler(self.log_file, encoding='utf-8')
        fh_all.setLevel(logging.INFO)

        # File handler for errors only (UTF-8 for emojis)
        fh_error = logging.FileHandler(self.error_file, encoding='utf-8')
        fh_error.setLevel(logging.ERROR)

        # Console handler (UTF-8 encoding)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.stream.reconfigure(encoding='utf-8')

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        fh_all.setFormatter(formatter)
        fh_error.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh_all)
        self.logger.addHandler(fh_error)
        self.logger.addHandler(ch)

    def log_info(self, message):
        """Log info message"""
        self.logger.info(f"[INFO] {message}")

    def log_success(self, message):
        """Log success message"""
        self.logger.info(f"[SUCCESS] {message}")

    def log_warning(self, message):
        """Log warning message"""
        self.logger.warning(f"[WARNING] {message}")

    def log_error(self, message, exception=None):
        """Log error message"""
        if exception:
            self.logger.error(f"[ERROR] {message} | Exception: {str(exception)}")
        else:
            self.logger.error(f"[ERROR] {message}")

    def log_critical(self, message, exception=None):
        """Log critical error and send alert"""
        if exception:
            self.logger.critical(f"[CRITICAL] {message} | Exception: {str(exception)}")
        else:
            self.logger.critical(f"[CRITICAL] {message}")

        # Send alert email
        self.send_alert_email(message, exception)

    def send_alert_email(self, message, exception=None):
        """Send alert email on critical error"""
        try:
            from config_secure import get_reporting_email_config

            email_config = get_reporting_email_config()

            subject = f"CRITICAL ALERT - FUELVIA SYSTEM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            body = f"""
CRITICAL ERROR DETECTED!
═══════════════════════════════════════════

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error Message:
{message}

Exception Details:
{str(exception) if exception else 'None'}

Log File: logs/errors.log

Action Required:
1. Check logs/errors.log for details
2. Investigate the issue
3. Restart the system if needed
4. Check system health

Status Page: https://fuelvia.app/status
Support: support@fuelvia.com

═══════════════════════════════════════════
This is an automated alert from Fuelvia System
            """

            msg = MIMEMultipart()
            msg['From'] = email_config['email']
            msg['To'] = email_config['email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['email'], email_config['password'])
                server.sendmail(email_config['email'], email_config['email'], msg.as_string())

            self.logger.info("✅ Alert email sent to admin")

        except Exception as e:
            self.logger.error(f"Failed to send alert email: {str(e)}")

    def get_recent_errors(self, lines=20):
        """Get recent errors from log"""
        try:
            with open(self.error_file, 'r') as f:
                return f.readlines()[-lines:]
        except:
            return []

    def clear_old_logs(self, days=30):
        """Clear logs older than specified days"""
        import glob
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        for log_file in glob.glob("logs/*.log*"):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                if file_time < cutoff:
                    os.remove(log_file)
                    self.logger.info(f"Cleared old log: {log_file}")
            except:
                pass


# Global logger instance
logger = ErrorLogger()
