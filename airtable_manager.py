import requests
from datetime import datetime, date
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME


class AirtableManager:
    def __init__(self):
        self.base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        self.headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json",
        }

    def _request(self, method, url=None, **kwargs):
        url = url or self.base_url
        try:
            resp = requests.request(method, url, headers=self.headers, **kwargs)
            if resp.status_code == 429:
                import time; time.sleep(30)
                resp = requests.request(method, url, headers=self.headers, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"  ❌ Airtable error: {e}")
            return None

    def create_lead(self, lead_data):
        score = lead_data.get("score", "N/A")
        reason = lead_data.get("score_reason", "")
        fields = {
            "Channel Name": str(lead_data.get("channel_name", "")),
            "Email": str(lead_data.get("email", "")),
            "Subscriber Count": int(lead_data.get("subscriber_count", 0)),
            "Location": str(lead_data.get("location", "")),
            "Niche": str(lead_data.get("niche", "")),
            "YouTube URL": str(lead_data.get("youtube_url", "")),
            "Status": "New",
            "Follow-up Stage": "Initial",
            "Date Added": date.today().strftime("%Y-%m-%d"),
            "Last Contact": date.today().strftime("%Y-%m-%d"),
            "Replied": False,
            "Notes": f"Claude Score: {score}/10 | {reason}",
        }
        result = self._request("POST", json={"fields": fields})
        return result.get("id") if result else None

    def check_duplicate(self, email):
        formula = f"LOWER({{Email}})=LOWER('{email}')"
        params = {"filterByFormula": formula, "maxRecords": 1}
        result = self._request("GET", params=params)
        if result and result.get("records"):
            return True, result["records"][0]["id"]
        return False, None

    def update_lead_status(self, record_id, status, follow_up_stage):
        url = f"{self.base_url}/{record_id}"
        fields = {
            "Status": status,
            "Follow-up Stage": follow_up_stage,
            "Last Contact": date.today().strftime("%Y-%m-%d"),
        }
        return self._request("PATCH", url, json={"fields": fields})

    def mark_replied(self, email):
        is_dup, record_id = self.check_duplicate(email)
        if record_id:
            url = f"{self.base_url}/{record_id}"
            fields = {
                "Replied": True,
                "Reply Date": date.today().strftime("%Y-%m-%d"),
                "Status": "Replied",
            }
            return self._request("PATCH", url, json={"fields": fields})
        return None

    def get_leads_for_followup(self, day):
        from datetime import timedelta
        target_date = (date.today() - timedelta(days=day)).strftime("%Y-%m-%d")
        if day == 1:
            status_filter = "Status='New'"
        elif day == 2:
            status_filter = "Status='Follow-up 1 Sent'"
        else:
            status_filter = "OR(Status='Follow-up 2 Sent',Status='Follow-up 1 Sent')"
        formula = f"AND({{Date Added}}='{target_date}',{{Replied}}=FALSE(),{status_filter})"
        params = {"filterByFormula": formula}
        result = self._request("GET", params=params)
        return result.get("records", []) if result else []

    def get_all_leads(self):
        records = []
        params = {}
        while True:
            result = self._request("GET", params=params)
            if not result:
                break
            records.extend(result.get("records", []))
            offset = result.get("offset")
            if not offset:
                break
            params["offset"] = offset
        return records

    def get_today_stats(self):
        today = date.today().strftime("%Y-%m-%d")
        all_records = self.get_all_leads()
        today_leads = [r for r in all_records if r["fields"].get("Date Added") == today]
        today_replies = [r for r in all_records if r["fields"].get("Reply Date") == today]
        status_counts = {}
        for r in all_records:
            s = r["fields"].get("Status", "New")
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "leads_today": len(today_leads),
            "replies_today": len(today_replies),
            "total_leads": len(all_records),
            "total_replies": sum(1 for r in all_records if r["fields"].get("Replied")),
            "status_counts": status_counts,
        }