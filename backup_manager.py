# ============================================================
# BACKUP MANAGER - Automatic SQLite backup + Notion sync
# ============================================================

import sqlite3
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from error_logger import logger


class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

        self.db_file = "leads_backup.db"
        self.init_backup_database()

    def init_backup_database(self):
        """Initialize SQLite backup database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Create leads table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                channel_name TEXT,
                email TEXT UNIQUE,
                youtube_url TEXT,
                subscriber_count INTEGER,
                niche TEXT,
                location TEXT,
                score INTEGER,
                status TEXT,
                date_added TEXT,
                last_contact TEXT,
                replied BOOLEAN DEFAULT 0,
                reply_message TEXT,
                reply_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create emails table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_email TEXT,
                from_account TEXT,
                email_type TEXT,
                subject TEXT,
                sent_at TIMESTAMP,
                status TEXT,
                FOREIGN KEY(lead_email) REFERENCES leads(email)
            )
            ''')

            # Create replies table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_email TEXT,
                reply_message TEXT,
                reply_at TIMESTAMP,
                FOREIGN KEY(lead_email) REFERENCES leads(email)
            )
            ''')

            conn.commit()
            conn.close()

            logger.log_success("Backup database initialized")

        except Exception as e:
            logger.log_error(f"Failed to initialize backup database: {str(e)}")

    def backup_lead(self, lead_data):
        """Backup a single lead to SQLite"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT OR REPLACE INTO leads (
                id, channel_name, email, youtube_url, subscriber_count,
                niche, location, score, status, date_added, last_contact,
                replied, reply_message, reply_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead_data.get('id'),
                lead_data.get('channel_name'),
                lead_data.get('email'),
                lead_data.get('youtube_url'),
                lead_data.get('subscriber_count', 0),
                lead_data.get('niche'),
                lead_data.get('location'),
                lead_data.get('score', 0),
                lead_data.get('status', 'New'),
                lead_data.get('date_added'),
                lead_data.get('last_contact'),
                lead_data.get('replied', False),
                lead_data.get('reply_message'),
                lead_data.get('reply_date'),
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.log_error(f"Failed to backup lead {lead_data.get('email')}: {str(e)}")

    def backup_email_sent(self, lead_email, from_account, email_type, subject):
        """Backup email sent record"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO emails_sent (lead_email, from_account, email_type, subject, sent_at, status)
            VALUES (?, ?, ?, ?, datetime('now'), 'sent')
            ''', (lead_email, from_account, email_type, subject))

            conn.commit()
            conn.close()

            logger.log_info(f"✅ Email backed up: {lead_email}")

        except Exception as e:
            logger.log_error(f"Failed to backup email: {str(e)}")

    def backup_reply(self, lead_email, reply_message):
        """Backup reply received"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO replies (lead_email, reply_message, reply_at)
            VALUES (?, ?, datetime('now'))
            ''', (lead_email, reply_message))

            conn.commit()
            conn.close()

            logger.log_info(f"✅ Reply backed up: {lead_email}")

        except Exception as e:
            logger.log_error(f"Failed to backup reply: {str(e)}")

    def create_full_backup(self):
        """Create full database backup file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"leads_backup_{timestamp}.db"

            shutil.copy(self.db_file, backup_file)

            logger.log_success(f"Full backup created: {backup_file}")
            self.cleanup_old_backups()

            return str(backup_file)

        except Exception as e:
            logger.log_error(f"Failed to create full backup: {str(e)}")
            return None

    def cleanup_old_backups(self, days=30):
        """Delete backups older than specified days"""
        try:
            cutoff = datetime.now() - timedelta(days=days)

            for backup_file in self.backup_dir.glob("*.db"):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff:
                        backup_file.unlink()
                        logger.log_info(f"Deleted old backup: {backup_file}")
                except:
                    pass

        except Exception as e:
            logger.log_error(f"Failed to cleanup old backups: {str(e)}")

    def get_all_leads(self):
        """Get all leads from backup database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM leads')
            columns = [description[0] for description in cursor.description]
            leads = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return leads

        except Exception as e:
            logger.log_error(f"Failed to get leads from backup: {str(e)}")
            return []

    def get_backup_stats(self):
        """Get backup database statistics"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM leads')
            total_leads = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM emails_sent')
            total_emails = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM replies')
            total_replies = cursor.fetchone()[0]

            conn.close()

            return {
                "total_leads": total_leads,
                "total_emails_sent": total_emails,
                "total_replies": total_replies,
            }

        except Exception as e:
            logger.log_error(f"Failed to get backup stats: {str(e)}")
            return {}


# Global backup manager instance
backup_manager = BackupManager()
