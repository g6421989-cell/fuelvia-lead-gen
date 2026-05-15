# ============================================================
# CTA DETECTOR - Parse Business CTAs from Video Data
# ============================================================
# Detects if channel is promoting services/coaching/products
# NOT relying on Claude, pure pattern matching

import re
from typing import Dict, List, Tuple

# Business CTAs
BUSINESS_CTCAS = {
    "booking": [
        r"(?:book|schedule|calendar|calendly)",
        r"(?:book\s*(?:a\s*)?(?:call|meeting|session|intro|consultation))",
        r"(?:click.*link|link.*bio)",
        r"(?:apply|register|enroll)",
    ],
    "contact": [
        r"(?:email|reach out|contact|message|dm|dm me)",
        r"(?:slide\s*(?:into\s*)?(?:my\s*)?dm)",
        r"(?:comment below|reply|respond)",
    ],
    "product": [
        r"(?:buy|purchase|order|get)",
        r"(?:link\s*in\s*(?:bio|description|comments))",
        r"(?:check\s*(?:out|below|link))",
        r"(?:limited|offer|exclusive|deal)",
    ],
    "pricing": [
        r"\$\d+(?:,\d{3})*",
        r"(?:price|cost|invest|budget)",
        r"(?:per\s*(?:month|year|session|hour))",
        r"(?:payment|pricing|rates)",
    ],
    "coaching": [
        r"(?:coaching|mentoring|consulting|advising)",
        r"(?:help\s*you|work\s*with|partner|collaborate)",
        r"(?:transformation|breakthrough|results)",
        r"(?:my\s*students|my\s*clients|case studies)",
    ],
    "authority": [
        r"(?:course|program|mastermind|community)",
        r"(?:join.*group|apply.*program|enroll)",
        r"(?:framework|system|method|process)",
    ],
}

# Anti-patterns (entertainment/hobby indicators)
ENTERTAINMENT_INDICATORS = [
    r"(?:vlog|vlogging|daily vlog)",
    r"(?:gaming|let's\s*play|gameplay)",
    r"(?:reaction|react|reacting)",
    r"(?:mukbang|asmr|prank)",
    r"(?:unboxing|review.*product)",
    r"(?:just\s*for\s*fun|hobby|bored)",
    r"(?:funny|comedy|entertaining|jokes?)",
]

# Strong B2B keywords
B2B_KEYWORDS = [
    "entrepreneur", "founder", "business owner", "executive", "manager",
    "agency", "consultant", "coach", "mentor", "expert",
    "revenue", "profit", "growth", "scale", "expand",
    "client", "customer", "lead", "conversion", "sales",
    "marketing", "strategy", "system", "process", "framework",
    "services", "retainer", "pricing", "offer", "solution",
]

def detect_ctacs_in_text(text: str) -> Dict[str, bool]:
    """
    Detect all CTA types in text
    Returns: {"booking": bool, "contact": bool, "product": bool, ...}
    """
    text_lower = text.lower()
    detected = {}

    for cta_type, patterns in BUSINESS_CTCAS.items():
        found = False
        for pattern in patterns:
            if re.search(pattern, text_lower):
                found = True
                break
        detected[cta_type] = found

    return detected

def has_entertainment_focus(title: str, description: str) -> bool:
    """
    Check if this is entertainment/hobby content
    """
    combined = f"{title} {description}".lower()

    for pattern in ENTERTAINMENT_INDICATORS:
        if re.search(pattern, combined):
            return True

    return False

def count_b2b_keywords(text: str) -> int:
    """
    Count B2B keywords in text
    """
    text_lower = text.lower()
    count = 0

    for keyword in B2B_KEYWORDS:
        if keyword in text_lower:
            count += 1

    return count

def score_ctas(videos_data: List[Dict]) -> Tuple[float, List[str]]:
    """
    Score CTA strength across recent videos

    Args:
        videos_data: List of video dicts with title, description

    Returns:
        (cta_score: 0-2.0, reasons: list of explanations)
    """
    if not videos_data:
        return 0.0, ["No video data available"]

    reasons = []
    total_cta_points = 0
    strong_cta_count = 0

    # Analyze first 5 videos (most recent)
    for i, video in enumerate(videos_data[:5]):
        title = video.get('title', '')
        description = video.get('description', '')

        # Check for entertainment focus (disqualifying)
        if has_entertainment_focus(title, description):
            reasons.append(f"Video {i+1}: Entertainment focus detected")
            continue

        # Detect CTAs
        detected_ctas = detect_ctacs_in_text(f"{title} {description}")
        cta_found = sum(detected_ctas.values())

        if cta_found >= 2:
            strong_cta_count += 1
            total_cta_points += 0.4
            reasons.append(f"Video {i+1}: Strong CTA ({cta_found} types detected)")
        elif cta_found == 1:
            total_cta_points += 0.2
            reasons.append(f"Video {i+1}: Weak CTA (1 type only)")
        else:
            reasons.append(f"Video {i+1}: No CTA detected")

        # Bonus for specific strong CTAs
        if detected_ctas.get('booking'):
            total_cta_points += 0.3
            reasons[-1] += " [BOOKING CTA!]"
        if detected_ctas.get('coaching'):
            total_cta_points += 0.3
            reasons[-1] += " [COACHING CTA!]"

    # Cap score at 2.0
    cta_score = min(total_cta_points, 2.0)

    # Bonus: if 3+ videos have CTAs
    if strong_cta_count >= 3:
        cta_score = min(cta_score + 0.5, 2.0)
        reasons.append("STRONG: 3+ videos with CTAs")

    return cta_score, reasons

def score_b2b_language(channel_description: str, video_descriptions: List[str]) -> Tuple[float, str]:
    """
    Score B2B language in channel description + videos

    Returns:
        (b2b_score: 0-1.0, reason: explanation)
    """
    all_text = channel_description + " " + " ".join(video_descriptions[:5])
    keyword_count = count_b2b_keywords(all_text)

    # Score: 0.1 per keyword (0-1.0)
    b2b_score = min(keyword_count * 0.1, 1.0)

    if keyword_count >= 8:
        reason = f"Strong B2B language ({keyword_count} keywords)"
    elif keyword_count >= 4:
        reason = f"Moderate B2B language ({keyword_count} keywords)"
    elif keyword_count >= 2:
        reason = f"Some B2B language ({keyword_count} keywords)"
    else:
        reason = "Minimal B2B language"

    return b2b_score, reason

def parse_pricing(videos_data: List[Dict]) -> Tuple[bool, str]:
    """
    Check if any video mentions pricing

    Returns:
        (has_pricing: bool, example_price: str)
    """
    for video in videos_data[:5]:
        description = video.get('description', '')

        # Look for price patterns: $XXX, $XXX/month, etc
        price_matches = re.findall(r'\$[\d,]+(?:/\w+)?', description)
        if price_matches:
            return True, price_matches[0]

    return False, None

if __name__ == "__main__":
    # Test
    test_title = "How to scale your agency to 6-figures"
    test_desc = "In this video, I show you the framework I use to help my clients scale to 6-figures. Book a call: calendly.com/john"

    combined_text = f"{test_title} {test_desc}"
    ctacs = detect_ctacs_in_text(combined_text)
    print(f"CTAs detected: {ctacs}")
    print(f"Entertainment focus: {has_entertainment_focus(test_title, test_desc)}")
    print(f"B2B keywords: {count_b2b_keywords(combined_text)}")
