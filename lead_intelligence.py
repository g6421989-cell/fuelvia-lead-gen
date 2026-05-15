# ============================================================
# LEAD INTELLIGENCE SYSTEM
# 1. Duplicate Prevention
# 2. Lead Freshness Tracking
# 3. Niche Health Dashboard
# 4. Auto-Expansion Suggestions
# ============================================================

from datetime import datetime, timedelta
from notion_manager import NotionManager
from error_logger import logger


class LeadIntelligence:
    def __init__(self):
        self.notion = NotionManager()

    # ============================================================
    # 1. DUPLICATE PREVENTION - Check before emailing
    # ============================================================

    def is_duplicate_contact(self, email, channel_name):
        """Check if we already contacted this channel"""
        try:
            all_leads = self.notion.get_all_leads()

            for lead in all_leads:
                props = lead.get('properties', {})
                lead_email = props.get('Email', {}).get('email', '')
                status = props.get('Status', {}).get('select', {}).get('name', '')

                if lead_email.lower() == email.lower():
                    # Already in system — any post-New status = already contacted
                    if status in ['Contacted', 'Follow-up Sent', 'Replied', 'Closed']:
                        return True, status  # Duplicate
                    return False, None  # In system but not contacted yet (New)

            return False, None  # Not in system

        except Exception as e:
            logger.log_error(f"Duplicate check error: {str(e)}")
            return False, None

    # ============================================================
    # 2. LEAD FRESHNESS TRACKING - Track contact history
    # ============================================================

    def get_lead_freshness(self, email):
        """Get when this lead was last contacted"""
        try:
            all_leads = self.notion.get_all_leads()

            for lead in all_leads:
                props = lead.get('properties', {})
                lead_email = props.get('Email', {}).get('email', '')

                if lead_email.lower() == email.lower():
                    status = props.get('Status', {}).get('select', {}).get('name', 'Unknown')
                    date_added = props.get('Date Added', {}).get('date', {}).get('start', '')

                    if date_added:
                        days_old = (datetime.now().date() - datetime.fromisoformat(date_added).date()).days
                        return {
                            'status': status,
                            'date_added': date_added,
                            'days_since_contact': days_old,
                            'is_fresh': days_old < 30  # Less than 30 days = fresh
                        }

            return None

        except Exception as e:
            logger.log_error(f"Freshness check error: {str(e)}")
            return None

    # ============================================================
    # 3. NICHE HEALTH DASHBOARD - Show which niches are running out
    # ============================================================

    def get_niche_health(self):
        """Get health status of each niche"""
        try:
            all_leads = self.notion.get_all_leads()

            # Count by niche and status
            niche_stats = {}

            for lead in all_leads:
                props = lead.get('properties', {})
                niche = props.get('Niche', {}).get('select', {}).get('name', 'Unknown')
                status = props.get('Status', {}).get('select', {}).get('name', 'New')

                if niche not in niche_stats:
                    niche_stats[niche] = {
                        'total': 0,
                        'contacted': 0,
                        'replied': 0,
                        'new': 0,
                        'health': 'Good'
                    }

                niche_stats[niche]['total'] += 1

                if status in ['Contacted', 'Follow-up Sent']:
                    niche_stats[niche]['contacted'] += 1
                elif status == 'Replied':
                    niche_stats[niche]['replied'] += 1
                elif status == 'New':
                    niche_stats[niche]['new'] += 1

            # Calculate health
            for niche, stats in niche_stats.items():
                remaining = stats['total'] - stats['contacted']

                if remaining > 100:
                    stats['health'] = '🟢 Excellent'
                    stats['health_score'] = 3
                elif remaining > 50:
                    stats['health'] = '🟡 Good'
                    stats['health_score'] = 2
                elif remaining > 20:
                    stats['health'] = '🟠 Fair'
                    stats['health_score'] = 1
                else:
                    stats['health'] = '🔴 Exhausted'
                    stats['health_score'] = 0

                stats['remaining'] = remaining
                stats['percentage_used'] = int((stats['contacted'] / stats['total'] * 100) if stats['total'] > 0 else 0)

            return niche_stats

        except Exception as e:
            logger.log_error(f"Niche health error: {str(e)}")
            return {}

    # ============================================================
    # 4. AUTO-EXPANSION SUGGESTIONS - Suggest next moves
    # ============================================================

    def get_expansion_suggestions(self):
        """Get suggestions for expanding to new niches/locations"""
        try:
            niche_health = self.get_niche_health()

            suggestions = {
                'niche_suggestions': [],
                'location_suggestions': [],
                'subscriber_suggestions': [],
                'urgency': 'Normal'
            }

            # Check which niches are exhausted
            exhausted_niches = [n for n, s in niche_health.items() if s['health_score'] == 0]
            fair_niches = [n for n, s in niche_health.items() if s['health_score'] == 1]

            if len(exhausted_niches) > 0:
                suggestions['urgency'] = 'URGENT - Expand now!'
                suggestions['niche_suggestions'] = [
                    f"🔴 {niche} is exhausted - expand to new niches",
                    "Add 3-5 new niches immediately",
                    "Consider E-Commerce, AI/ML, Fitness Coach as alternatives"
                ]

            elif len(fair_niches) > 2:
                suggestions['urgency'] = 'High - Start expanding'
                suggestions['niche_suggestions'] = [
                    f"🟠 {len(fair_niches)} niches running low",
                    "Start testing 2-3 new niches",
                    "Rotate through different niche combinations"
                ]

            # Location suggestions
            suggestions['location_suggestions'] = [
                "✅ Start with Tier 1 (USA, UK, Canada, Australia)",
                "Expand to Europe (Germany, France, Netherlands) after 30 days",
                "Add India & Singapore after 60 days for volume"
            ]

            # Subscriber range suggestions
            suggestions['subscriber_suggestions'] = [
                "Start: < 50K range (more availability)",
                "After 60 days: Expand to 100K+ for premium leads",
                "Mix ranges: 10K-50K (quantity) + 50K-100K (quality)"
            ]

            return suggestions

        except Exception as e:
            logger.log_error(f"Expansion suggestions error: {str(e)}")
            return {}

    # ============================================================
    # SUMMARY REPORT
    # ============================================================

    def get_intelligence_report(self):
        """Get complete intelligence report"""
        try:
            return {
                'niche_health': self.get_niche_health(),
                'expansion_suggestions': self.get_expansion_suggestions(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Intelligence report error: {str(e)}")
            return {}


# Global instance
lead_intelligence = LeadIntelligence()
