# ============================================================
# CLAUDE HELPERS — Fuelvia Email Writing (v3 — Anti-Template)
# ============================================================
# Every email is unique. Six anti-template rules enforced:
#   1. Opener = insight, not compliment
#   2. Pain = exact content type match
#   3. Offer wording rotates every email
#   4. Closing line has personality + rotates
#   5. Anti-generic check: could this go to anyone else?
#   6. Tone shifts based on subscriber count
# ============================================================

import requests
import json
import random
import settings_store
from config import SENDER_NAME, COMPANY_NAME


# ── API ────────────────────────────────────────────────────────

def call_claude(prompt: str, max_tokens: int = 600) -> str | None:
    # Read LIVE from settings store so UI changes apply without restart
    api_key  = settings_store.get("CLAUDE_API_KEY")
    base_url = settings_store.get("CLAUDE_BASE_URL")
    model    = settings_store.get("CLAUDE_MODEL")

    if not api_key:
        print("  [ERROR] Claude API key not set (configure in Settings)")
        return None
    try:
        response = requests.post(
            base_url,
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [ERROR] Claude API error: {e}")
        return None


def _parse_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None


def _fmt_subs(subs: int) -> str:
    if subs >= 1_000_000:
        return f"{subs/1_000_000:.1f}M"
    if subs >= 1_000:
        n = subs / 1_000
        return f"{n:.1f}K" if n % 1 else f"{int(n)}K"
    return str(subs)


def _build_video_block(videos_data) -> str:
    if not videos_data or not isinstance(videos_data, list):
        return "  (no recent videos available)"
    lines = []
    for i, v in enumerate(videos_data[:5], 1):
        if not isinstance(v, dict):
            continue
        title = v.get("title", "").strip()
        if title:
            lines.append(f"  {i}. {title}")
    return "\n".join(lines) if lines else "  (no titles available)"


def _sub_tier(subs: int) -> str:
    if subs < 3000:
        return (
            "UNDER 3K SUBSCRIBERS — peer-to-peer tone. "
            "Write as if talking to someone just finding their footing. "
            "No authority angle. Friendly, direct, equal-to-equal. "
            "Acknowledge they're building something real."
        )
    if subs < 10000:
        return (
            "3K–10K SUBSCRIBERS — growing creator tone. "
            "Write as if talking to someone who is getting serious and starting to see traction. "
            "They know their content works, the bottleneck is now output and quality. "
            "Position the offer as the next logical step for someone at their stage."
        )
    return (
        "ABOVE 10K SUBSCRIBERS — established creator tone. "
        "Write as if talking to someone who already has proof of concept and needs to scale production. "
        "They don't need convincing the content works — they need execution support. "
        "Treat them as a serious operator, not a hobbyist."
    )


_DAY1_SUBJECTS = [
    "quick question",
    "quick idea",
    "wrote something for you",
    "free edit for you",
]

_OFFER_VARIANTS = [
    "send us one raw clip and we'll edit it completely free",
    "drop us your worst footage — we'll turn it around for free",
    "pick any video you have sitting unedited and we'll handle it at no charge",
    "one raw recording — we handle everything from there, completely free",
    "send over one piece of raw footage and we'll edit it, no invoice, nothing owed",
    "hand us one unedited file — we'll do the full edit for free",
    "drop us any raw video and we'll send back a finished edit at zero cost",
]

_CLOSING_VARIANTS = [
    "If you hate it, ghost us. Fair?",
    "No invoice. No pitch. Just footage and an edit back in 24 hours.",
    "Worst case you get a free edit. Best case we work together.",
    "We do the work first. You decide after.",
    "No strings. Just send the raw file.",
    "You keep the edit either way. We just want to show you what we can do.",
    "One file. 24 hours. You decide if it's worth continuing.",
]

_FORBIDDEN = (
    "leverage, synergy, touch base, circle back, value proposition, "
    "excited to connect, following up on my previous email, just checking in, "
    "as per my last email, I hope this email finds you well, "
    "I came across your channel, I noticed, I hope this finds you well, "
    "I love your content, Great video, Amazing content, Your content is great"
)


# ── DAY 1 COLD EMAIL ───────────────────────────────────────────

def write_personalized_initial_email(
    channel_data: dict,
    videos_data: list,
) -> tuple[str, str]:
    """
    Write a hyper-personalised Day 1 cold email. Six anti-template
    rules applied at the prompt level to guarantee every email
    is unique and creator-specific.
    """
    channel_name  = channel_data.get("channel_name", "Creator")
    niche         = channel_data.get("niche", "content creation")
    subs          = channel_data.get("subscriber_count", 0)
    days_inactive = channel_data.get("days_since_upload", 0)
    subs_fmt      = _fmt_subs(subs)
    video_block   = _build_video_block(videos_data)
    subject       = random.choice(_DAY1_SUBJECTS)
    offer_variant = random.choice(_OFFER_VARIANTS)
    closing       = random.choice(_CLOSING_VARIANTS)
    tone_rule     = _sub_tier(subs)

    prompt = f"""You are writing a cold outreach email for {SENDER_NAME} at Fuelvia (fuelviaa.com).
Fuelvia is a video editing and content production agency. They edit raw footage into scroll-stopping videos — reels, shorts, YouTube long-form, talking-head, cinematic — delivered in 24-72 hours.

━━━━ CREATOR INFO ━━━━
Channel     : {channel_name}
Niche       : {niche}
Subscribers : {subs_fmt}
Days since last upload: {days_inactive}

Recent video titles:
{video_block}

━━━━ TONE RULE (follow exactly based on their size) ━━━━
{tone_rule}

━━━━ EMAIL STRUCTURE — 5 paragraphs, plain text, UNDER 120 WORDS ━━━━

PARAGRAPH 1 — INSIGHT OPENER (not a compliment)
Do NOT say the video was good, great, interesting, or impressive.
Instead, make an observation that shows you understood the CONTENT.
Read the video title and ask: what does this topic actually mean for someone making content about it?
GOOD example for "How I Automated My Business in 30 Days":
→ "Automating an entire business in 30 days means you either have bulletproof systems or you broke something along the way — either way that video earned its watch time."
BAD example: "Great video on automation. I really enjoyed it."
The opener must feel like it came from someone who actually engaged with that specific topic.
Reference {channel_name} or the video title naturally.

PARAGRAPH 2 — EXACT PAIN POINT (match their content type precisely)
Look at their video titles and identify what TYPE of content they make:
- Business systems/automation creators → pain: making complex workflows look simple and engaging on camera
- Coaching/mindset creators → pain: keeping talking-head content visually dynamic and not losing viewers
- Course/education creators → pain: making long recordings feel punchy and high-retention
- Finance/investing creators → pain: making data-heavy content visually engaging without losing accuracy
- Fitness/health creators → pain: production quality gap between their expertise and how it looks on screen
- Agency/freelancer creators → pain: consistent posting schedule while running client work simultaneously
Match the pain to what you actually see in their titles. NEVER use a generic pain point.

PARAGRAPH 3 — WHO WE ARE (one sentence only)
"We're Fuelvia, a video editing agency that helps [their content type] creators turn raw footage into scroll-stopping content — delivered in 24 hours."
Customise "[their content type]" to match their actual niche.

PARAGRAPH 4 — THE FREE OFFER
Use this exact offer wording (already chosen for this email — do not change it):
"{offer_variant}"
Then add: If they love it they can talk about working together. If they don't, Fuelvia never contacts them again.
Make it feel like a genuine no-risk gift.

PARAGRAPH 5 — CLOSING LINE
Use this exact closing (already chosen — do not change it):
"{closing}"

Sign off: {SENDER_NAME}, Fuelvia

━━━━ ANTI-TEMPLATE CHECK (do this before finalising) ━━━━
Ask yourself: Could this exact email be sent to a different creator by just swapping the name?
If yes — rewrite it. The email MUST contain at least one detail so specific to {channel_name} and their content that it could not work for anyone else.
That specific detail should be in paragraph 1 or 2.

━━━━ ABSOLUTE RULES ━━━━
- UNDER 120 WORDS total (count every word)
- Plain text only — no bullets, no bold, no links, zero formatting
- NEVER use: {_FORBIDDEN}
- No generic openers. No "I hope" anything.
- Goal: get a reply. Nothing else.

Subject is already chosen: "{subject}"

Respond ONLY as valid JSON — no markdown, no explanation:
{{"subject": "{subject}", "body": "<the 5-paragraph email, under 120 words>"}}"""

    data = _parse_json(call_claude(prompt, max_tokens=600))
    if data:
        body = data.get("body", "").strip()
        if body:
            return subject, body

    # ── FALLBACK ──────────────────────────────────────────────
    first_title = (
        videos_data[0].get("title", "your recent video")
        if videos_data and isinstance(videos_data[0], dict)
        else "your recent video"
    )
    return subject, (
        f'"{first_title}" — {channel_name} is clearly building something serious in the {niche} space.\n\n'
        f"The gap for most creators at your stage isn't ideas — it's turning raw footage into "
        f"something that actually holds attention.\n\n"
        f"We're Fuelvia, a video editing agency that helps {niche} creators turn raw footage "
        f"into scroll-stopping content — delivered in 24 hours.\n\n"
        f"{offer_variant}. If you love it we talk. If not, we disappear.\n\n"
        f"{closing}\n\n"
        f"{SENDER_NAME}, Fuelvia"
    )


# ── DAY 2 FOLLOW-UP ────────────────────────────────────────────

def write_personalized_followup_1(
    channel_data: dict,
    day1_email_body: str = "",
) -> tuple[str, str]:
    """
    Day 2 follow-up — warmer, shorter, different angle.
    Under 70 words. References different video. Soft close.
    """
    channel_name = channel_data.get("channel_name", "Creator")
    niche        = channel_data.get("niche", "content")
    subs_fmt     = _fmt_subs(channel_data.get("subscriber_count", 0))
    closing      = random.choice(_CLOSING_VARIANTS)

    day1_block = (
        f"DAY 1 EMAIL SENT:\n{day1_email_body[:800].strip()}"
        if day1_email_body
        else "(original email not available)"
    )

    prompt = f"""You sent this cold email 2 days ago — no reply.
Write a short warm follow-up for {SENDER_NAME} at Fuelvia (fuelviaa.com).

Channel: {channel_name} | Niche: {niche} | Subs: {subs_fmt}

{day1_block}

RULES:
- UNDER 70 WORDS (strict)
- Warmer and softer than Day 1 — like a genuine human check-in
- Do NOT repeat the same pitch verbatim
- Acknowledge you sent something before — keep it light
- Free edit offer still mentioned briefly
- Reference a video title from Day 1's context if possible — but a DIFFERENT one
- End with this exact closing line (do not change): "{closing}"
- Plain text only. No formatting.
- NEVER use: {_FORBIDDEN}

Sign off: {SENDER_NAME}, Fuelvia

Respond ONLY as valid JSON:
{{"subject": "Re: {channel_name}", "body": "<follow-up under 70 words>"}}"""

    data = _parse_json(call_claude(prompt, max_tokens=300))
    if data:
        s = data.get("subject", "").strip()
        b = data.get("body", "").strip()
        if s and b:
            return s, b

    closing_fb = random.choice(_CLOSING_VARIANTS)
    return (
        f"Re: {channel_name}",
        f"Wanted to pop back in — the free edit for {channel_name} is still open. "
        f"One raw file, we turn it around completely free.\n\n"
        f"{closing_fb}\n\n"
        f"{SENDER_NAME}, Fuelvia",
    )


# ── LEGACY ALIAS ──────────────────────────────────────────────
write_personalized_followup_2 = write_personalized_followup_1


# ── KEYWORD VARIATION GENERATOR ───────────────────────────────

def generate_keyword_variations(
    niche_key: str,
    existing_keywords: list,
    used_keywords: list = None,
) -> list:
    """
    Generate 7 fresh YouTube search query variations for a niche.

    Called ONCE at scrape start — one API call, zero config changes.
    Returns a list of new query strings to append to the keyword pool.
    Falls back to [] silently if Claude is unavailable so scraping
    continues uninterrupted with the original keywords.

    used_keywords: all queries used in previous scrape runs for this niche
                   — Claude will not repeat them (Solution 5).

    Why this helps:
      - Surfaces sub-niches and synonyms not in config.py
      - Uses current YouTube language patterns Claude knows
      - Every scrape session gets different angles (used_keywords avoidance)
      - 7 extra queries = up to ~7x more keyword-location pairs
    """
    if not existing_keywords:
        return []

    # Combine existing config keywords + previous-run used keywords to avoid
    all_avoid = list(existing_keywords) + (used_keywords or [])
    avoid_str = "\n".join(f"- {k}" for k in all_avoid[:25])

    previously_note = ""
    if used_keywords:
        prev_str = "\n".join(f"- {k}" for k in used_keywords[:15])
        previously_note = f"""
Previously used queries (NEVER repeat these — generate completely different angles):
{prev_str}
"""

    prompt = f"""You help find YouTube creators in the "{niche_key}" space who post videos to attract coaching or consulting clients.

Generate exactly 7 YouTube search queries that would find creators in this niche or closely related sub-niches.
{previously_note}
Do NOT repeat anything from this list:
{avoid_str}

Rules:
- Each query must find people who ACTIVELY POST YouTube videos
- Include words like "YouTube", "tips", "channel", "how to", or "advice" where natural
- Cover sub-niches, synonyms, adjacent angles, or more specific breakdowns of "{niche_key}"
- Keep each query 3-7 words long
- Vary the style — some with "YouTube", some without, some more specific
- The goal is FRESH results — explore angles NOT covered by the avoid list above

Respond ONLY as a JSON array of exactly 7 strings, no explanation, no markdown:
["query one", "query two", "query three", "query four", "query five", "query six", "query seven"]"""

    raw = call_claude(prompt, max_tokens=300)
    if not raw:
        return []

    try:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        variations = json.loads(raw[start:end])
        if isinstance(variations, list):
            clean = [v.strip() for v in variations if isinstance(v, str) and v.strip()]
            # Remove any that are too close to existing/used keywords (dedup)
            avoid_lower = {k.lower() for k in all_avoid}
            return [v for v in clean if v.lower() not in avoid_lower]
    except Exception:
        pass

    return []
