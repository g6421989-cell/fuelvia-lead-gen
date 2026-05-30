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

# Email mailboxes that are NOT a person's name
_GENERIC_LOCALPARTS = {
    "info", "hello", "hi", "hey", "contact", "team", "admin", "mail", "email",
    "support", "business", "official", "media", "studio", "yt", "youtube",
    "sales", "help", "noreply", "no", "reply", "the", "hq", "agency", "co",
    "social", "marketing", "booking", "bookings", "inquiries", "enquiries",
}
# First words that signal a brand/channel, not a person
_NON_NAME_WORDS = {
    "the", "tech", "official", "real", "daily", "my", "team", "studio", "media",
    "channel", "tv", "news", "review", "reviews", "mr", "mrs", "ms", "dr", "prof",
    "digital", "creative", "online", "best", "top", "pro", "global",
}


def _greeting_name(channel_name: str, email: str = "") -> str:
    """
    Best-effort HUMAN first name from all available data.
      1) channel/display name — only if it looks like a person (≤2 words, not a brand word)
      2) email local-part (kartik@.. -> Kartik, john.doe@.. -> John)
    Returns '' when no confident human name exists → caller uses 'Hey there,'.
    Never returns a brand word or a generic role mailbox (info@, team@, ...).
    """
    # 1) Channel / display name (text before a separator)
    base = channel_name or ""
    for sep in ["-", "|", "–", "—", ":", "(", "/", ",", "@"]:
        if sep in base:
            base = base.split(sep)[0]
    toks = base.strip().split()
    if (toks and len(toks) <= 2 and toks[0].isalpha()
            and 2 <= len(toks[0]) <= 15 and toks[0].lower() not in _NON_NAME_WORDS):
        return toks[0].capitalize()

    # 2) Email local-part
    if email and "@" in email:
        local = email.split("@")[0]
        for ch in "._-0123456789+":
            local = local.replace(ch, " ")
        for part in local.split():
            if part.isalpha() and 2 <= len(part) <= 15 and part.lower() not in _GENERIC_LOCALPARTS:
                return part.capitalize()

    return ""


def write_personalized_initial_email(
    channel_data: dict,
    videos_data: list,
) -> tuple[str, str]:
    """
    Write the Day-1 cold email in Fuelvia's house style (casual, pain-point-led,
    NEVER a pitch). Both the SUBJECT and BODY are personalised every time using
    the lead's channel/niche/recent content. Signed by the Founder of Fuelvia.

    This prompt IS the persistent "house style" — every email Claude writes
    references it, so the voice stays consistent without re-teaching it.
    Returns (subject, body).
    """
    channel_name  = channel_data.get("channel_name", "there")
    niche         = channel_data.get("niche", "content creation")
    subs          = channel_data.get("subscriber_count", 0)
    lead_email    = channel_data.get("email", "")
    subs_fmt      = _fmt_subs(subs)
    video_block   = _build_video_block(videos_data)

    prompt = f"""You are the in-house cold-email writer for Fuelvia (fuelviaa.com) — a content +
video team that handles scripting, editing and posting so creators, coaches and experts can grow
their personal brand and pull in leads WITHOUT doing the content grind themselves.
You write every email as {SENDER_NAME}, Founder of Fuelvia.

━━━━ WHO YOU'RE EMAILING ━━━━
Name / Channel : {channel_name}
Email          : {lead_email or "(unknown)"}
Niche          : {niche}
Audience size  : {subs_fmt}
Recent videos  :
{video_block}

━━━━ HOUSE STYLE — this is the exact voice, follow it every time ━━━━
Write like a real founder firing off a quick, casual note to a peer. NOT a marketer. NOT a pitch.
Study these two reference patterns and write a FRESH email in the same spirit (never copy verbatim):

PATTERN A — short, question-led:
  Hey [first name],
  Quick one — are you trying to pull more leads out of your {niche} content?
  If yes, we might be able to help — we handle content + strategy for {niche} folks.
  If no, no worries, just delete this. If maybe, let's talk.

PATTERN B — pain-point-led:
  Subject: the content problem most {niche} creators hit
  Hey [first name],
  Most {niche} creators are in the same boat — they know content matters but don't have time to
  script, edit and post consistently. So they either don't post, or post stuff that doesn't convert.
  We fix that by running the whole thing — scripting, editing, posting — so you focus on the
  business and your brand actually brings in leads.
  Only works if you're serious about it. If you are, let's talk.

━━━━ HARD RULES (every email) ━━━━
1. THE FIRST EMAIL IS NEVER A PITCH. Open by naming a SPECIFIC pain or asking a sharp question
   that's genuinely true for {channel_name}'s kind of content. No compliments ("love your channel"),
   no "free edit" gimmick, no "I hope this finds you well", no selling in line one.
2. CASUAL, not corporate. Short, human sentences. Like texting a peer you respect. Never stiff,
   never salesy, never "professional-formal".
3. SPECIFIC to them — use what their recent videos are actually about so this email could NOT be
   copy-pasted to a random creator.
4. SHORT — under ~90 words total.
5. LOW-PRESSURE close with an out (e.g. "no worries if not" / "if maybe, let's talk" /
   "only if you're serious"). Never pushy, never "book a call now".
6. GREETING — work out a real first name from the data, in this order:
   (a) the channel/display name "{channel_name}" (e.g. "Kartik Dhiman - Coach" → "Kartik"), then
   (b) the email address "{lead_email or '(unknown)'}" (e.g. "kartik@gmail.com" → "Kartik",
       "john.doe@site.com" → "John").
   If you find a clear HUMAN first name, greet "Hey {{Name}},".
   If it's a brand/company or only a generic mailbox (info@, team@, hello@, a channel like
   "Tech Review Central") and you can't confidently pull a person's name, just write "Hey there,".
   NEVER invent a name and NEVER use a brand word or company name as the greeting name.
7. Plain text. No bullets, no bold, no links in the body.
8. Sign off EXACTLY like this (two lines):
   {SENDER_NAME}
   Founder, Fuelvia
9. PERSONALISE THE SUBJECT too — short, lowercase, pain- or curiosity-led, never salesy.
   Good: "the content problem {niche} creators hit" / "quick one about your {niche} content"
   Bad : "Grow your brand with Fuelvia!" / "Boost your leads today!"

NEVER use: {_FORBIDDEN}

Respond ONLY as valid JSON, nothing else:
{{"subject": "<personalised casual pain/curiosity subject>", "body": "<the casual email under 90 words, signed 'Founder, Fuelvia'>"}}"""

    data = _parse_json(call_claude(prompt, max_tokens=600))
    if data:
        subject = (data.get("subject") or "").strip()
        body    = (data.get("body") or "").strip()
        if subject and body:
            return subject, body

    # ── FALLBACK (same casual, pain-led house style) ──────────
    name    = _greeting_name(channel_name, lead_email)
    greet   = f"Hey {name}," if name else "Hey there,"
    subject = f"the content problem {niche} creators hit"
    body = (
        f"{greet}\n\n"
        f"Most {niche} creators are in the same boat — they know content matters but don't have "
        f"the time to script, edit and post consistently. So it either doesn't get done, or it goes "
        f"out half-baked and doesn't convert.\n\n"
        f"We handle the whole thing for you — scripting, editing, posting — so your brand actually "
        f"brings in leads while you stay focused on the business.\n\n"
        f"No worries if it's not for you. If maybe, let's talk.\n\n"
        f"{SENDER_NAME}\nFounder, Fuelvia"
    )
    return subject, body


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
