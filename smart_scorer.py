# ============================================================
# SMART SCORER - Intelligent Lead Scoring (NO Claude)
# ============================================================
# Scores based on REAL YouTube data:
# - Video frequency
# - CTA strength
# - Audience engagement
# - B2B language
# Replaces Claude for lead qualification (saves API $ & time)

import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from cta_detector import (
    score_ctas, score_b2b_language, parse_pricing,
    has_entertainment_focus
)

def calculate_activity_score(last_video_date: str, days_since_video: int) -> Tuple[float, str]:
    """
    Score based on posting frequency/recency (0-2.0)

    Very Active (last 14 days): 2.0
    Active (last 30 days): 1.5
    Moderate (last 90 days): 1.0
    Slow (90-180 days): 0.5
    Inactive (180+ days): 0.0
    """
    if days_since_video <= 14:
        return 2.0, "Very active (posted <14 days ago) 🔥"
    elif days_since_video <= 30:
        return 1.5, "Active (posted <30 days ago) ⚡"
    elif days_since_video <= 90:
        return 1.0, "Moderate activity (posted <90 days ago)"
    elif days_since_video <= 180:
        return 0.5, "Slow (posted 90-180 days ago)"
    else:
        return 0.0, "Inactive (no video 180+ days) ❌"

def calculate_upload_frequency_score(video_dates: List[str]) -> Tuple[float, str]:
    """
    Score based on upload consistency (0-1.5)

    1+ per week: 1.5 (very consistent)
    Bi-weekly: 1.0 (consistent)
    Monthly: 0.5 (slow)
    Sporadic: 0.0
    """
    if len(video_dates) < 2:
        return 0.0, "Not enough data"

    # Calculate average days between uploads (first 5 videos)
    dates = []
    for date_str in video_dates[:5]:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            dates.append(dt)
        except:
            pass

    if len(dates) < 2:
        return 0.0, "Cannot calculate frequency"

    # Calculate average days between videos
    dates.sort(reverse=True)
    gaps = []
    for i in range(len(dates) - 1):
        gap = (dates[i] - dates[i+1]).days
        gaps.append(gap)

    avg_gap = sum(gaps) / len(gaps)

    if avg_gap <= 7:
        return 1.5, f"Very consistent uploads (~every {int(avg_gap)} days) 🚀"
    elif avg_gap <= 14:
        return 1.0, f"Consistent uploads (~every {int(avg_gap)} days)"
    elif avg_gap <= 30:
        return 0.5, f"Regular uploads (~every {int(avg_gap)} days)"
    else:
        return 0.0, f"Sporadic uploads (~every {int(avg_gap)} days)"

def calculate_subscriber_score(subscriber_count: int) -> Tuple[float, str]:
    """
    Score based on subscriber count (0-1.0)

    Sweet spot: 5k-100k (1.0)
    Small but established: 1k-5k (0.8)
    Growing: 100k-500k (0.8)
    Very large: 500k+ (0.5 - less personal)
    """
    if 5000 <= subscriber_count <= 100000:
        return 1.0, f"Perfect range ({subscriber_count:,} subs) ⭐"
    elif 1000 <= subscriber_count < 5000:
        return 0.8, f"Smaller but established ({subscriber_count:,} subs)"
    elif 100000 < subscriber_count <= 500000:
        return 0.8, f"Growing audience ({subscriber_count:,} subs)"
    elif subscriber_count < 1000:
        return 0.3, f"Too small ({subscriber_count:,} subs)"
    else:  # > 500k
        return 0.5, f"Very large ({subscriber_count:,} subs) - may be less personal"

def calculate_engagement_score(videos_data: List[Dict]) -> Tuple[float, str]:
    """
    Score based on audience engagement (0-1.0)

    High engagement (5%+): 1.0
    Medium (2-5%): 0.7
    Low (<2%): 0.3
    """
    if not videos_data:
        return 0.0, "No video data"

    engagement_ratios = []

    for video in videos_data[:5]:
        view_count = video.get('view_count', 0)
        like_count = video.get('like_count', 0)
        comment_count = video.get('comment_count', 0)

        if view_count > 0:
            # Engagement = (likes + comments) / views
            engagement = (like_count + comment_count) / view_count
            engagement_ratios.append(engagement)

    if not engagement_ratios:
        return 0.0, "Cannot calculate engagement"

    avg_engagement = sum(engagement_ratios) / len(engagement_ratios)

    if avg_engagement >= 0.05:
        return 1.0, f"High engagement ({avg_engagement*100:.1f}%) - active audience 🔥"
    elif avg_engagement >= 0.02:
        return 0.7, f"Medium engagement ({avg_engagement*100:.1f}%)"
    else:
        return 0.3, f"Low engagement ({avg_engagement*100:.1f}%)"

def intelligent_score_channel(
    channel_data: Dict,
    videos_data: List[Dict],
    days_since_video: int
) -> Dict:
    """
    MAIN SCORING FUNCTION
    Scores channel based on REAL YouTube data, not Claude guesses

    Returns:
        {
            "score": 0-10,
            "qualified": bool (true if score 5+),
            "breakdown": {
                "activity": score,
                "frequency": score,
                "subscribers": score,
                "ctas": score,
                "b2b_language": score,
                "engagement": score
            },
            "reasons": [list of explanations],
            "confidence": 0-100 (how confident we are)
        }
    """

    reasons = []
    scores = {}

    # ===== IMMEDIATE DISQUALIFIERS =====
    # If any of these are true, return score 0
    channel_name = channel_data.get('channel_name', '')
    channel_desc = channel_data.get('description', '')
    email = channel_data.get('email')

    if not email:
        return {
            "score": 0,
            "qualified": False,
            "reason": "No email found",
            "breakdown": {},
            "reasons": ["❌ No email in description"],
            "confidence": 95
        }

    # Check for entertainment-only channels
    if videos_data:
        combined_titles = " ".join([v.get('title', '') for v in videos_data[:5]])
        combined_desc = " ".join([v.get('description', '') for v in videos_data[:5]])

        if has_entertainment_focus(combined_titles, combined_desc):
            return {
                "score": 2,
                "qualified": False,
                "reason": "Entertainment/hobby focus (not B2B business)",
                "breakdown": {},
                "reasons": ["❌ Entertainment focus detected (gaming, vlogging, comedy, etc)"],
                "confidence": 90
            }

    # Check if completely inactive
    if days_since_video > 365:
        return {
            "score": 1,
            "qualified": False,
            "reason": f"Channel inactive for {days_since_video} days",
            "breakdown": {},
            "reasons": [f"❌ No video in {days_since_video} days (abandoned)"],
            "confidence": 98
        }

    # ===== SCORING FACTORS =====

    # FACTOR 1: Activity (0-2.0)
    activity_score, activity_reason = calculate_activity_score(
        channel_data.get('last_video_date'),
        days_since_video
    )
    scores['activity'] = activity_score
    reasons.append(activity_reason)

    # FACTOR 2: Upload Frequency (0-1.5)
    frequency_score, frequency_reason = calculate_upload_frequency_score(
        [v.get('published_at', '') for v in videos_data]
    )
    scores['frequency'] = frequency_score
    reasons.append(frequency_reason)

    # FACTOR 3: Subscriber Count (0-1.0)
    subscriber_score, subscriber_reason = calculate_subscriber_score(
        channel_data.get('subscriber_count', 0)
    )
    scores['subscribers'] = subscriber_score
    reasons.append(subscriber_reason)

    # FACTOR 4: CTA Strength (0-2.0) - THIS IS THE GOLDMINE
    cta_score, cta_reasons = score_ctas(videos_data)
    scores['ctas'] = cta_score
    reasons.extend(cta_reasons)

    # FACTOR 5: B2B Language (0-1.0)
    b2b_score, b2b_reason = score_b2b_language(
        channel_desc,
        [v.get('description', '') for v in videos_data]
    )
    scores['b2b_language'] = b2b_score
    reasons.append(b2b_reason)

    # FACTOR 6: Engagement (0-1.0)
    engagement_score, engagement_reason = calculate_engagement_score(videos_data)
    scores['engagement'] = engagement_score
    reasons.append(engagement_reason)

    # ===== WEIGHTED SCORING =====
    # Total possible: 10 points
    #
    # Activity:        2.0 (20%)  - Must be recent
    # Frequency:       1.5 (15%)  - Consistency
    # Subscribers:     1.0 (10%)  - Size matters
    # CTAs:            2.0 (20%)  - STRONGEST INDICATOR
    # B2B Language:    1.0 (10%)  - Shows business focus
    # Engagement:      1.0 (10%)  - Audience quality
    # BONUS:           0.5 (5%)   - For strong indicators
    # ─────────────────────────────
    # TOTAL:          10.0 (100%)

    total_score = (
        activity_score * (2.0 / 2.0) +        # Normalize to max
        frequency_score * (1.5 / 1.5) +
        subscriber_score * (1.0 / 1.0) +
        cta_score * (2.0 / 2.0) +              # CTAs are 20% of score
        b2b_score * (1.0 / 1.0) +
        engagement_score * (1.0 / 1.0)
    )

    # ===== BONUS POINTS =====
    # Pricing mentioned
    has_pricing, price_example = parse_pricing(videos_data)
    if has_pricing:
        total_score += 0.5
        reasons.append(f"💰 PRICING MENTIONED: {price_example}")

    # Multiple CTAs across many videos
    if cta_score >= 1.5:
        total_score += 0.2
        reasons.append("⭐ STRONG: Multiple CTAs detected across videos")

    # Cap at 10
    total_score = min(total_score, 10.0)

    # ===== QUALIFICATION LOGIC =====
    # NOT just score >= 5, but smarter rules
    qualified = False
    confidence = 70

    if total_score >= 7:
        # High confidence qualification
        qualified = True
        confidence = 95
    elif total_score >= 5.5:
        # Medium-high score
        if cta_score >= 1.0 and activity_score >= 1.0:
            qualified = True
            confidence = 85
    elif total_score >= 5:
        # At threshold - needs strong indicators
        if (cta_score >= 1.5 or b2b_score >= 0.8) and activity_score >= 1.0:
            qualified = True
            confidence = 75

    return {
        "score": round(total_score, 1),
        "qualified": qualified,
        "reason": f"Score {round(total_score, 1)}/10 - {'✅ QUALIFIED' if qualified else '❌ NOT QUALIFIED'}",
        "breakdown": scores,
        "reasons": reasons,
        "confidence": confidence
    }

if __name__ == "__main__":
    # Test scoring
    test_channel = {
        "channel_name": "John's Business Coaching",
        "subscriber_count": 25000,
        "description": "Help entrepreneurs scale to 6-figures. Work with me: calendly.com/john",
        "last_video_date": "2024-05-03T12:00:00Z",
        "email": "john@example.com"
    }

    test_videos = [
        {
            "title": "How to scale your agency to 6-figures",
            "description": "Book your free consultation: calendly.com/john. My clients make 6-figures...",
            "view_count": 5000,
            "like_count": 500,
            "comment_count": 200,
            "published_at": "2024-05-03T12:00:00Z"
        },
        {
            "title": "Top 5 marketing strategies for coaches",
            "description": "Join my coaching program. Link in bio.",
            "view_count": 8000,
            "like_count": 800,
            "comment_count": 300,
            "published_at": "2024-04-26T12:00:00Z"
        }
    ]

    result = intelligent_score_channel(test_channel, test_videos, 5)
    print(f"\nChannel: {test_channel['channel_name']}")
    print(f"Score: {result['score']}/10")
    print(f"Qualified: {result['qualified']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nReasons:")
    for reason in result['reasons']:
        print(f"  {reason}")
