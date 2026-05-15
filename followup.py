"""
FUELVIA FOLLOW-UP & REPLY SYSTEM - 2-EMAIL MAX PER LEAD
- FIX 1: Global EmailRotator (not recreated per call)
- FIX 2: Follow-ups use SAME account as cold email (fetch from Notion)
- FIX 3: 2-email max per lead (cold + 1 follow-up only)
  * Day 0: Cold email sent
  * Day 2: Follow-up sent (from same account)
  * Day 3+: Marked as Closed if no reply
- Checks ONLY yesterday's leads for replies
- Notion database updates
- Consolidated report via reporting email ONLY

USAGE: python followup.py
"""

import time
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config_secure import EMAIL_ROTATION_DELAY, SENDER_NAME, SENDER_TITLE, OUTREACH_ACCOUNTS
from notion_manager import NotionManager
from email_helpers import send_outreach_email, send_report_email, ReplyChecker
from claude_helpers import write_personalized_followup_1
from error_logger import logger


class FollowUpSystem:
    def __init__(self):
        self.notion = NotionManager()
        self.reply_checker = ReplyChecker()
        self.stats = {
            "followup_sent": 0,
            "closed_no_response": 0,
            "replies_found": []
        }

    def send_followup_1(self):
        """
        Send personalized follow-up to Day 2 leads
        FIX 2: Uses SAME account that sent cold email (from Notion 'Email Sent From' field)
        """
        print("\n📧 Sending Follow-ups (Day 2 leads - Claude personalized)...")
        records = self.notion.get_leads_for_followup_1()

        if not records:
            print("  No Day 2 leads to follow up.")
            return

        leads = [self.notion.extract_lead_data(record) for record in records]

        for idx, lead in enumerate(leads):
            # Use pre-written email if available
            if "_prepared_subject" in lead and "_prepared_body" in lead:
                print(f"  ✅ Using pre-written follow-up for {lead['channel_name']}...")
                subject = lead["_prepared_subject"]
                body = lead["_prepared_body"]
            else:
                print(f"  ✍️  Claude writing follow-up for {lead['channel_name']}...")
                subject, body = write_personalized_followup_1({
                    "channel_name": lead["channel_name"],
                    "niche": lead["niche"],
                    "score": lead["score"]
                })

            # FIX 2: Get the account that sent the cold email
            sent_from_email = self.notion.get_email_sent_from(lead["email"])

            if not sent_from_email:
                print(f"  ⚠️  No 'Email Sent From' record for {lead['email']} - skipping")
                continue

            # Find the account object matching the email
            account = None
            for acc in OUTREACH_ACCOUNTS:
                if acc['email'].lower() == sent_from_email.lower():
                    account = acc
                    break

            if not account:
                print(f"  ⚠️  Account {sent_from_email} not found in config - skipping")
                continue

            # FIX 2: Send from the SAME account as original cold email
            try:
                success, sender = send_outreach_email(
                    lead["email"],
                    subject,
                    body,
                    account=account,
                    is_followup=True  # Mark as follow-up (required account)
                )

                if success:
                    # Update Notion
                    self.notion.update_lead_status(lead["id"], "Follow-up Sent", "F1")
                    self.notion.update_email_sent(lead["id"], 2)

                    self.stats["followup_sent"] += 1
                    print(f"  ✅ Follow-up sent to {lead['channel_name']} from {sender}")
                else:
                    print(f"  ❌ Failed to send follow-up to {lead['email']}")

                # While waiting, write next email in parallel
                if idx < len(leads) - 1:
                    next_lead = leads[idx + 1]
                    next_name = next_lead["channel_name"]

                    print(f"  ⏳ Waiting {EMAIL_ROTATION_DELAY}s (Claude writing next follow-up)...")
                    start_time = time.time()

                    if "_prepared_subject" not in next_lead:
                        print(f"     ✍️  Preparing follow-up for {next_name}...")
                        next_subject, next_body = write_personalized_followup_1({
                            "channel_name": next_lead["channel_name"],
                            "niche": next_lead["niche"],
                            "score": next_lead["score"]
                        })
                        next_lead["_prepared_subject"] = next_subject
                        next_lead["_prepared_body"] = next_body
                        print(f"     ✅ Follow-up ready for {next_name}")

                    # Wait for remaining time
                    elapsed = time.time() - start_time
                    remaining = EMAIL_ROTATION_DELAY - elapsed
                    if remaining > 0:
                        time.sleep(remaining)

            except ValueError as e:
                print(f"  ❌ {str(e)}")
            except Exception as e:
                print(f"  ❌ Failed to send follow-up to {lead['email']}: {e}")

    def mark_closed_no_response(self):
        """
        FIX 3: Mark Day 3+ leads as Closed (2-email max policy)
        After cold email (Day 0) + follow-up (Day 2), if no reply by Day 3, mark Closed
        """
        print("\n🔄 Marking Day 3+ leads as Closed (2-email max policy)...")
        records = self.notion.get_no_response_candidates()

        for record in records:
            lead = self.notion.extract_lead_data(record)
            self.notion.update_lead_status(lead["id"], "Closed", "No Reply")
            self.stats["closed_no_response"] += 1

        print(f"  📊 Marked {self.stats['closed_no_response']} leads as Closed (no response after 2 emails)")

    def check_yesterday_replies(self):
        """Check ONLY yesterday's leads for replies"""
        print("\n🔍 Checking yesterday's leads for replies...")

        # Get all leads added yesterday
        yesterday = date.today() - timedelta(days=1)
        all_records = self.notion.get_all_leads()
        yesterday_leads = [r for r in all_records
                          if r.get("properties", {}).get("Date Added", {}).get("date", {}).get("start") == yesterday.isoformat()]

        if not yesterday_leads:
            print("  No leads added yesterday to check.")
            return

        print(f"  Total leads added yesterday: {len(yesterday_leads)}")

        # Extract lead data for checking
        leads_to_check = [self.notion.extract_lead_data(r) for r in yesterday_leads]

        # Check for replies
        replies = self.reply_checker.check_for_replies(leads_to_check)

        # Update Notion with replies
        for reply in replies:
            self.notion.mark_replied(
                reply["email"],
                reply_message=reply["full_message"],
                reply_time=reply["reply_time"]
            )
            self.stats["replies_found"].append(reply)

        print(f"  📊 Found {len(replies)} replies from yesterday's leads")

    def generate_consolidated_report(self):
        """Generate consolidated report with 2-email policy"""
        system_stats = self.notion.get_system_stats()

        report = "═" * 70 + "\n"
        report += "FUELVIA DAILY FOLLOW-UP REPORT\n"
        report += f"{datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
        report += "═" * 70 + "\n\n"

        # SECTION 1: Today's Follow-ups
        report += "📧 TODAY'S FOLLOW-UPS SENT\n"
        report += "─" * 70 + "\n\n"
        report += f"✅ Follow-ups (Day 2 leads): {self.stats['followup_sent']} emails sent\n"
        report += f"❌ Marked 'Closed' (Day 3+, 2-email max): {self.stats['closed_no_response']} leads\n\n"
        report += f"📊 Total emails sent today: {self.stats['followup_sent']}\n\n"
        report += "💡 Policy: 2 emails maximum per lead (cold email + 1 follow-up)\n"
        report += "   After 2 emails with no reply, lead is marked as Closed\n\n"

        # SECTION 2: Yesterday's Replies
        report += "═" * 70 + "\n"
        report += "🎉 YESTERDAY'S REPLIES\n"
        report += "═" * 70 + "\n\n"

        yesterday_leads_count = len([r for r in self.notion.get_all_leads()
                                    if r.get("properties", {}).get("Date Added", {}).get("date", {}).get("start")
                                    == (date.today() - timedelta(days=1)).isoformat()])

        reply_rate = (len(self.stats["replies_found"]) / max(1, yesterday_leads_count) * 100)
        report += f"Total leads checked: {yesterday_leads_count}\n"
        report += f"New replies: {len(self.stats['replies_found'])} ({reply_rate:.1f}% reply rate)\n\n"

        if self.stats["replies_found"]:
            for i, reply in enumerate(self.stats["replies_found"], 1):
                report += "─" * 70 + "\n"
                report += f"REPLY #{i}\n\n"
                report += f"Channel: {reply['channel_name']}\n"
                report += f"Email: {reply['email']}\n"
                report += f"Score: {reply['score']}/10\n"
                report += f"Replied: {reply['reply_time']}\n\n"
                report += f"Message:\n{reply['message']}\n\n"
        else:
            report += "No replies from yesterday's leads.\n\n"

        # SECTION 3: Overall Stats
        report += "═" * 70 + "\n"
        report += "📊 OVERALL SYSTEM STATS\n"
        report += "═" * 70 + "\n\n"
        report += f"Total leads in system: {system_stats['total_leads']}\n"
        report += f"Total replied: {system_stats['total_replied']} ({system_stats['reply_rate']:.1f}%)\n\n"
        report += "Status breakdown:\n"

        for status, count in system_stats["status_counts"].items():
            report += f"  - {status}: {count}\n"

        report += "\n" + "═" * 70 + "\n"

        return report

    def send_report(self, report_body):
        """Send consolidated report from reporting email"""
        subject = f"📊 Follow-up Report - {self.stats['followup_sent']} Emails, {len(self.stats['replies_found'])} Replies"

        send_report_email(
            "Fuelviaa01@gmail.com",
            subject,
            report_body
        )

    def run(self):
        """Execute all operations"""
        print("\n" + "=" * 70)
        print("  FUELVIA FOLLOW-UP & REPLY SYSTEM - 2-EMAIL MAX POLICY")
        print("=" * 70)

        # Execute follow-ups and reply checks
        self.mark_closed_no_response()
        self.send_followup_1()
        self.check_yesterday_replies()

        # Generate and send report
        print("\n📨 Generating consolidated report...")
        report_body = self.generate_consolidated_report()
        print("\n" + report_body)

        print("\n📨 Sending consolidated report email...")
        self.send_report(report_body)

        print("\n" + "=" * 70)
        print("✅ Follow-up system complete!")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    system = FollowUpSystem()
    system.run()
