# ============================================================
# NOTION DATABASE MANAGER - All CRM Operations (ROBUST)
# ============================================================

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, date, timedelta
import time
import settings_store


def _split_rich_text(text: str, chunk: int = 1990) -> list:
    """Split a long string into Notion rich_text blocks (max 2000 chars each)."""
    if not text:
        return []
    parts = [text[i:i+chunk] for i in range(0, len(text), chunk)]
    return [{"text": {"content": p}} for p in parts]


class NotionManager:
    def __init__(self):
        # Read LIVE from settings store so UI changes apply without restart
        self.api_key = settings_store.get("NOTION_API_KEY")
        self.database_id = settings_store.get("NOTION_DATABASE_ID")
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        # Create session with connection pooling & retry strategy
        self.session = self._create_session()

    def _create_session(self):
        """Create requests session with retry strategy for resilience"""
        session = requests.Session()

        # Retry strategy: exponential backoff for transient errors
        retry_strategy = Retry(
            total=3,  # 3 retries max
            backoff_factor=1,  # 1s, 2s, 4s delays
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these
            allowed_methods=["GET", "POST", "PATCH"]  # Methods to retry
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _request(self, method, endpoint, **kwargs):
        """Make request to Notion API with robust error handling & retries"""
        url = f"{self.base_url}{endpoint}"
        timeout = kwargs.pop("timeout", 60)  # Longer timeout for stability

        attempt = 0
        max_attempts = 4  # 1 initial + 3 retries

        while attempt < max_attempts:
            attempt += 1
            try:
                resp = self.session.request(
                    method, url,
                    headers=self.headers,
                    timeout=timeout,
                    **kwargs
                )

                # Handle rate limiting (429)
                if resp.status_code == 429:
                    wait_time = 60
                    print(f"  ⚠️  Notion rate limited (attempt {attempt}/{max_attempts}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue  # Retry

                # Handle server errors (5xx) - retry
                if resp.status_code >= 500:
                    if attempt < max_attempts:
                        wait_time = 2 ** (attempt - 1)  # Exponential backoff
                        print(f"  ⚠️  Notion server error ({resp.status_code}). Retry {attempt}/{max_attempts} in {wait_time}s...")
                        time.sleep(wait_time)
                        continue  # Retry

                # Check for client errors (4xx except 429)
                if resp.status_code >= 400:
                    try:
                        error_detail = resp.json()
                        print(f"  ❌ Notion error ({resp.status_code}): {error_detail.get('message', 'Unknown error')}")
                    except:
                        print(f"  ❌ Notion error ({resp.status_code}): {resp.text[:200]}")
                    return None

                # Success
                return resp.json() if resp.text else {}

            except requests.exceptions.Timeout:
                if attempt < max_attempts:
                    wait_time = 2 ** (attempt - 1)
                    print(f"  ⚠️  Notion timeout. Retry {attempt}/{max_attempts} in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ❌ Notion timeout after {max_attempts} attempts")
                    return None

            except requests.exceptions.ConnectionError as e:
                if attempt < max_attempts:
                    wait_time = 2 ** (attempt - 1)
                    print(f"  ⚠️  Connection error. Retry {attempt}/{max_attempts} in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ❌ Connection failed after {max_attempts} attempts")
                    return None

            except requests.exceptions.SSLError as e:
                if attempt < max_attempts:
                    wait_time = 2 ** (attempt - 1)
                    print(f"  ⚠️  SSL error (connection unstable). Retry {attempt}/{max_attempts} in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ❌ SSL error persists after {max_attempts} attempts")
                    return None

            except requests.exceptions.RequestException as e:
                print(f"  ❌ Notion request error: {str(e)[:100]}")
                return None

        return None

    def create_lead(self, lead_data):
        """Add new lead to Notion database"""
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Channel Name": {
                    "title": [{"text": {"content": lead_data.get("channel_name", "")}}]
                },
                "Email": {
                    "email": lead_data.get("email") or None   # Notion rejects empty string
                },
                "YouTube URL": {
                    "url": lead_data.get("youtube_url") or None   # Notion rejects empty string for URL fields
                },
                "Subscriber Count": {
                    "number": int(lead_data.get("subscriber_count", 0))
                },
                "Niche": {
                    "select": {"name": lead_data.get("niche", "Business Coach")}
                },
                "Location": {
                    "rich_text": [{"text": {"content": lead_data.get("location", "")}}]
                },
                "Score": {
                    "number": int(lead_data.get("score", 5))
                },
                "Status": {
                    "select": {"name": lead_data.get("status", "New")}
                },
                "Date Added": {
                    "date": {"start": date.today().isoformat()}
                },
                # NOTE: Last Contact is intentionally NOT set on create.
                # It is only set when an email is actually sent (update_lead_status).
                # Setting it here would corrupt analytics by making new leads
                # appear as already contacted.
                "Replied": {
                    "checkbox": False
                },
                "Notes": {
                    "rich_text": [{"text": {"content": lead_data.get("score_reason", "")}}]
                },
                "Email Sent From": {
                    "rich_text": [{"text": {"content": lead_data.get("email_sent_from", "")}}]
                }
            }
        }

        result = self._request("POST", "/pages", json=payload)
        return result.get("id") if result else None

    def check_duplicate(self, email):
        """Check if email already exists"""
        payload = {
            "filter": {
                "property": "Email",
                "email": {"equals": email}
            }
        }
        result = self._request(
            "POST",
            f"/databases/{self.database_id}/query",
            json=payload
        )

        if result and result.get("results"):
            return True, result["results"][0]["id"]
        return False, None

    def archive_lead(self, page_id):
        """Archive a lead (Notion soft-delete → Trash, recoverable ~30 days)."""
        return self._request("PATCH", f"/pages/{page_id}", json={"archived": True})

    def update_lead_status(self, page_id, status, follow_up_stage=None):
        """Update lead status in Notion"""
        properties = {
            "Status": {"select": {"name": status}},
            "Last Contact": {"date": {"start": date.today().isoformat()}}
        }

        if follow_up_stage:
            properties["Follow-up Stage"] = {
                "rich_text": [{"text": {"content": follow_up_stage}}]
            }

        payload = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def update_email_sent(self, page_id, email_count):
        """Update last contact date (Email Count & Last Email Date are tracking-only)"""
        properties = {
            "Last Contact": {"date": {"start": date.today().isoformat()}}
        }
        payload = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def update_email_sent_from(self, page_id, account_email):
        """Update which account sent the cold email (for follow-ups to use same account)"""
        properties = {
            "Email Sent From": {
                "rich_text": [{"text": {"content": account_email}}]
            }
        }
        payload = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def get_email_sent_from(self, email):
        """Get which account sent the cold email for a lead"""
        is_dup, page_id = self.check_duplicate(email)
        if not page_id:
            return None

        all_leads = self.get_all_leads()
        for lead in all_leads:
            if lead.get("id") == page_id:
                props = lead.get("properties", {})
                email_sent_from = props.get("Email Sent From", {}).get("rich_text", [])
                if email_sent_from:
                    return email_sent_from[0].get("text", {}).get("content", "")
        return None

    def mark_replied(self, email, reply_message="", reply_time=None):
        """Mark lead as replied"""
        is_dup, page_id = self.check_duplicate(email)
        if not page_id:
            return None

        # Handle reply_time as string or datetime
        if reply_time:
            reply_date = reply_time if isinstance(reply_time, str) else reply_time.isoformat()
        else:
            reply_date = datetime.now().isoformat()

        properties = {
            "Replied": {"checkbox": True},
            "Reply Date": {"date": {"start": reply_date}},
            "Status": {"select": {"name": "Replied"}},
            "Last Contact": {"date": {"start": date.today().isoformat()}}
        }

        if reply_message:
            # Notion rich_text blocks max 2000 chars each — split into chunks
            # Note: actual Notion property name has a trailing space — "Reply Message "
            properties["Reply Message "] = {
                "rich_text": _split_rich_text(reply_message)
            }

        payload = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def save_day1_email_body(self, page_id: str, body: str):
        """Save the cold email body Claude wrote to Day 1 Email Body field."""
        if not body:
            return None
        payload = {
            "properties": {
                "Day 1 Email Body": {
                    "rich_text": _split_rich_text(body)
                }
            }
        }
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def mark_followup1_sent(self, page_id: str):
        """After sending follow-up: status → Follow-up 1, Day 2 Sent = True, Last Contact = today."""
        payload = {
            "properties": {
                "Status":       {"select": {"name": "Follow-up 1"}},
                "Day 2 Sent":   {"checkbox": True},
                "Last Contact": {"date": {"start": date.today().isoformat()}},
            }
        }
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def update_reply_message(self, email, reply_message):
        """Update only the reply message body for an existing replied lead (no status change)."""
        is_dup, page_id = self.check_duplicate(email)
        if not page_id or not reply_message:
            return None
        payload = {
            "properties": {
                "Reply Message ": {
                    "rich_text": _split_rich_text(reply_message)
                }
            }
        }
        return self._request("PATCH", f"/pages/{page_id}", json=payload)

    def get_leads_by_date_and_status(self, target_date, status):
        """Get leads added on specific date with specific status (paginated)."""
        return self._query_all({
            "and": [
                {"property": "Date Added", "date":     {"equals": target_date.isoformat()}},
                {"property": "Status",     "select":   {"equals": status}},
                {"property": "Replied",    "checkbox": {"equals": False}},
            ]
        })

    def get_leads_for_followup_1(self):
        """Get yesterday's Contacted leads that haven't replied (for automated daily cron)"""
        return self.get_leads_by_date_and_status(date.today() - timedelta(days=1), "Contacted")

    def get_all_contacted_leads(self):
        """
        Get ALL leads with Status='Contacted' that haven't replied.
        No date filter — for the manual 'Send Follow-ups' button.
        Leads with Status='Replied' or Replied=True are excluded automatically.
        Uses _query_all() so leads 101+ are not silently lost.
        """
        return self._query_all({
            "and": [
                {"property": "Status",  "select":   {"equals": "Contacted"}},
                {"property": "Replied", "checkbox": {"equals": False}},
            ]
        })

    def get_leads_for_followup_2(self):
        """Get 2-days-ago leads that have had F1 sent (paginated)."""
        two_days_ago = date.today() - timedelta(days=2)
        return self._query_all({
            "and": [
                {"property": "Date Added", "date":     {"equals": two_days_ago.isoformat()}},
                {"property": "Status",     "select":   {"equals": "Follow-up 1 Sent"}},
                {"property": "Replied",    "checkbox": {"equals": False}},
            ]
        })

    def get_no_response_candidates(self):
        """Get leads 3+ days old not yet marked no-response (paginated)."""
        three_days_ago = date.today() - timedelta(days=3)
        return self._query_all({
            "and": [
                {"property": "Date Added", "date":     {"before": three_days_ago.isoformat()}},
                {"property": "Status",     "select":   {"equals": "Follow-up Sent"}},
                {"property": "Replied",    "checkbox": {"equals": False}},
            ]
        })

    def _query_all(self, filter_payload: dict = None) -> list:
        """
        Paginated Notion query — fetches ALL matching records, not just first 100.
        All filtered query methods must use this instead of a single _request() call.
        Notion returns max 100 per page; without pagination leads 101+ are silently lost.
        """
        payload      = {"page_size": 100}
        if filter_payload:
            payload["filter"] = filter_payload
        all_records  = []
        start_cursor = None

        while True:
            if start_cursor:
                payload["start_cursor"] = start_cursor

            result = self._request(
                "POST",
                f"/databases/{self.database_id}/query",
                json=payload
            )

            if not result:
                break

            all_records.extend(result.get("results", []))

            if result.get("has_more"):
                start_cursor = result.get("next_cursor")
            else:
                break

        return all_records

    def get_all_leads(self):
        """Get all leads from database (paginated)."""
        return self._query_all()

    def get_system_stats(self):
        """Get overall system statistics"""
        all_records = self.get_all_leads()

        total_leads = len(all_records)
        total_replied = sum(1 for r in all_records
                           if r.get("properties", {}).get("Replied", {}).get("checkbox"))

        status_counts = {}
        for r in all_records:
            # Fixed: Status is a "select" field, not "status" field
            status = (((r.get("properties") or {}).get("Status") or {}).get("select") or {}).get("name") or "New"
            status_counts[status] = status_counts.get(status, 0) + 1

        reply_rate = (total_replied / total_leads * 100) if total_leads > 0 else 0

        return {
            "total_leads": total_leads,
            "total_replied": total_replied,
            "reply_rate": reply_rate,
            "status_counts": status_counts
        }

    def extract_lead_data(self, record):
        """Extract lead data from Notion record"""
        props = record.get("properties", {})
        return {
            "id": record.get("id"),
            "channel_name": self._extract_text(props.get("Channel Name")),
            "email": props.get("Email", {}).get("email", ""),
            "score": props.get("Score", {}).get("number", 5),
            "niche": props.get("Niche", {}).get("select", {}).get("name", ""),
            "youtube_url": props.get("YouTube URL", {}).get("url", ""),
            "subscriber_count": props.get("Subscriber Count", {}).get("number", 0),
            "status": props.get("Status", {}).get("select", {}).get("name", "New"),
        }

    def _extract_text(self, field):
        """Extract text from Notion rich_text or title field"""
        if not field:
            return ""

        if "title" in field:
            return "".join([block.get("text", {}).get("content", "")
                          for block in field.get("title", [])])
        elif "rich_text" in field:
            return "".join([block.get("text", {}).get("content", "")
                          for block in field.get("rich_text", [])])
        return ""
