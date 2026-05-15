# ============================================================
# SCRAPER ENGINE v2 — Precision Targeting
# ============================================================
# RULES:
# 1. Hard limit 30 max (enforced in API)
# 2. Stop at exact target — not before, not after
# 3. One keyword-location combo at a time
# 4. Break ALL loops when target is reached
# 5. Check email BEFORE qualification (save API quota)
# 6. Live log shows "Found X of Y"
# 7. Graceful exhaustion if all combos searched
# ============================================================

import re
import time
from datetime import datetime, timezone
from googleapiclient.discovery import build

from config import (
    YOUTUBE_APIS, NICHE_OPTIONS, NICHE_SEARCH_TERMS,
    LOCATION_OPTIONS, SUBSCRIBER_RANGES,
)
from notion_manager import NotionManager
from youtube_enricher import get_videos_for_channel, days_since_last_video
from channel_qualifier import qualify_channel, extract_email_from_all_sources
from channel_blacklist import is_blacklisted, add_to_blacklist, blacklist_size

DEFAULT_TARGET_LEADS = 30


# ── Helpers ───────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _evt(type_: str, message: str, data: dict = None) -> dict:
    e = {"type": type_, "message": message, "time": _now()}
    if data:
        e["data"] = data
    return e


def _get_youtube(api_index: int):
    key = YOUTUBE_APIS[api_index % len(YOUTUBE_APIS)]
    return build("youtube", "v3", developerKey=key), api_index


def _get_channel(youtube, channel_id: str):
    """Fetch basic channel info: name, subs, description, uploads playlist."""
    try:
        resp = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id,
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        item  = items[0]
        desc  = item["snippet"].get("description", "")
        subs  = int(item["statistics"].get("subscriberCount", 0))
        uploads = (
            item.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
        )
        return {
            "channel_name":        item["snippet"]["title"],
            "subscriber_count":    subs,
            "description":         desc,
            "youtube_url":         f"https://youtube.com/channel/{channel_id}",
            "channel_id":          channel_id,
            "uploads_playlist_id": uploads,
        }
    except Exception:
        return None


# ── Main generator ────────────────────────────────────────

def scrape_leads(niche_key: str, location_key: str, sub_range_key: str, max_leads: int = None):
    """
    Generator — yields event dicts until exactly max_leads are found.

    RULES:
    2. Stop at exact target
    3. One keyword-location combo at a time
    4. Break ALL loops when target reached
    5. Check email BEFORE qualification
    6. Live log shows "Found X of Y"
    7. Graceful exhaustion message
    """
    target_leads = max_leads if max_leads and max_leads > 0 else DEFAULT_TARGET_LEADS

    start_ts  = datetime.now()
    keywords  = NICHE_SEARCH_TERMS.get(niche_key, [niche_key])
    loc_list  = LOCATION_OPTIONS.get(location_key, [""])
    sub_min, sub_max = SUBSCRIBER_RANGES.get(sub_range_key, (1000, 20000))

    # ── Initial stats ──────────────────────────────────────
    bl_size = blacklist_size()
    yield _evt("info", f"Niche: {niche_key}  |  Location: {location_key}")
    yield _evt("info", f"Subscriber range: {sub_range_key}")
    yield _evt("info", f"Keywords ({len(keywords)}): {', '.join(keywords)}")
    yield _evt("info", f"RULE 2: Target exactly {target_leads} leads with valid emails")
    yield _evt("info", f"RULE 3: Searching one keyword-location combo at a time")
    yield _evt("info", f"Blacklist: {bl_size} channels permanently skipped from previous runs")

    api_index = 0
    youtube, api_index = _get_youtube(api_index)
    notion    = NotionManager()

    seen_ids         = set()   # dedupes within this run
    blacklist_hits   = 0       # channels skipped by permanent blacklist
    qualified        = []      # list of fully-enriched lead dicts
    channels_scanned = 0
    target_reached   = False   # flag to break all loops

    # ── RULE 3: Create keyword-location pairs ──────────────
    keyword_location_pairs = []
    for keyword in keywords:
        for loc in loc_list:
            keyword_location_pairs.append((keyword, loc if loc else "Global"))

    yield _evt("info", f"Will search {len(keyword_location_pairs)} keyword-location combinations")

    # ── PHASE 1: FIND LEADS (one combo at a time) ─────────
    for pair_idx, (keyword, loc) in enumerate(keyword_location_pairs, 1):
        if target_reached:
            break

        query = f"{keyword} {loc}".strip() if loc != "Global" else keyword
        yield _evt("info", f"[{pair_idx}/{len(keyword_location_pairs)}] Searching: '{query}'")

        next_page = None
        page_num  = 0

        while len(qualified) < target_leads and page_num < 15:
            # ─ Search call ───────────────────────────────
            try:
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "channel",
                    "maxResults": 50,
                    "relevanceLanguage": "en",
                }
                if next_page:
                    params["pageToken"] = next_page

                resp  = youtube.search().list(**params).execute()
                items = resp.get("items", [])
                if not items:
                    break

            except Exception as e:
                if "quotaExceeded" in str(e) or "403" in str(e):
                    api_index = (api_index + 1) % len(YOUTUBE_APIS)
                    youtube, api_index = _get_youtube(api_index)
                    yield _evt("warning", f"Search API quota hit — rotated to key #{api_index + 1}/{len(YOUTUBE_APIS)}")
                    time.sleep(1)
                    continue
                else:
                    yield _evt("error", f"Search failed for '{query}': {str(e)[:160]}")
                    break

            # ─ Per-channel processing ─────────────────────
            for item in items:
                if len(qualified) >= target_leads:  # ── RULE 2: Stop at exact target
                    target_reached = True
                    break

                cid = item["snippet"]["channelId"]

                # ── In-run dedup ─────────────────────────
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)

                # ── Permanent blacklist check (zero API cost) ──
                if is_blacklisted(cid):
                    blacklist_hits += 1
                    continue

                # ── Get basic channel info ───────────────
                details = _get_channel(youtube, cid)
                if not details:
                    continue

                subs = details["subscriber_count"]
                if subs < sub_min or (sub_max and subs > sub_max):
                    continue

                channels_scanned += 1
                name   = details["channel_name"]
                subs_k = f"{subs/1000:.1f}K" if subs >= 1000 else str(subs)

                yield _evt("info", f"  Scanning [{channels_scanned}]: {name} ({subs_k} subs)")

                # ── RULE 5: Check email FIRST (before qualification) ──
                email = extract_email_from_all_sources(
                    details.get("description", ""),
                    []  # Don't need video data just for email check
                )
                if not email:
                    yield _evt("info", f"    Skip {name}: no email found in description")
                    continue

                # ── Get video data for qualification ─────
                videos = []
                for _attempt in range(len(YOUTUBE_APIS)):
                    try:
                        videos = get_videos_for_channel(
                            youtube, cid,
                            uploads_playlist_id=details.get("uploads_playlist_id"),
                            max_videos=5,
                        )
                        break
                    except Exception as ve:
                        if "quotaExceeded" in str(ve) or "403" in str(ve):
                            api_index = (api_index + 1) % len(YOUTUBE_APIS)
                            youtube, api_index = _get_youtube(api_index)
                            yield _evt("warning", f"Video API quota hit — rotated to key #{api_index + 1}")
                        else:
                            yield _evt("error", f"Video fetch error ({name}): {str(ve)[:120]}")
                            break

                days = days_since_last_video(videos)
                details.update({
                    "days_since_last_video": days,
                    "videos_data":           videos,
                    "niche":                 keyword,
                    "location":              loc,
                })

                # ── Qualification check ──────────────────
                result = qualify_channel(details, videos, days)

                if not result["qualified"]:
                    reason = result["reason"]
                    yield _evt("warning", f"    Skip {name}: {reason}")
                    continue

                # ── Duplicate check against Notion ──────
                try:
                    is_dup, _ = notion.check_duplicate(email)
                    if is_dup:
                        yield _evt("warning", f"    Skip {name}: {email} already in database")
                        add_to_blacklist(cid, name)
                        continue
                except Exception as de:
                    yield _evt("error", f"Notion duplicate check failed ({name}): {str(de)[:100]}")
                    continue

                # ── QUALIFIED ✓ ─────────────────────────
                details["email"]        = email
                details["score"]        = result["score"]
                details["score_reason"] = result["reason"]
                qualified.append(details)

                found = len(qualified)
                # ── RULE 6: Live log shows progress ──
                yield _evt("success",
                    f"Found {found} of {target_leads} requested leads — {name}",
                    {"channel": name, "email": email, "score": result["score"]},
                )

                time.sleep(0.15)

                # ── RULE 4: Check if target reached after each lead ──
                if len(qualified) >= target_leads:
                    target_reached = True
                    break

            next_page = resp.get("nextPageToken")
            if not next_page:
                break
            page_num += 1
            time.sleep(0.3)

        # ── RULE 6: Message when stopping mid-search ──
        if target_reached:
            yield _evt("info", f"Target reached — stopping all API calls. Canceling remaining {len(keyword_location_pairs) - pair_idx} keyword-location combos.")
            break

    # ── PHASE 2: SAVE LEADS TO NOTION + BLACKLIST ─────────
    if not qualified:
        elapsed = int((datetime.now() - start_ts).total_seconds())
        yield _evt("error",
            f"No qualified leads found after scanning {channels_scanned} channels "
            f"({blacklist_hits} skipped by blacklist). "
            f"Try a broader niche or wider subscriber range.",
        )
        yield _evt("complete", "Search complete — 0 leads found", {
            "leads_found": 0, "channels_scanned": channels_scanned,
            "time_seconds": elapsed, "niche": niche_key,
        })
        return

    found_count = len(qualified)
    yield _evt("info", "─" * 50)

    # ── RULE 7: Graceful exhaustion message ──
    if found_count < target_leads:
        yield _evt("info", f"Search complete — found {found_count} leads out of {target_leads} requested.")
        yield _evt("info", f"All keyword and location combinations exhausted. Saving {found_count} lead(s).")
    else:
        yield _evt("info", f"Target reached — {found_count} leads found. Saving to Notion + blacklist...")

    saved = 0
    for i, lead in enumerate(qualified, 1):
        name  = lead["channel_name"]
        email = lead["email"]
        cid   = lead.get("channel_id", "")
        try:
            notion.create_lead({
                "channel_name":     name,
                "email":            email,
                "youtube_url":      lead.get("youtube_url", ""),
                "subscriber_count": lead.get("subscriber_count", 0),
                "niche":            lead.get("niche", niche_key),
                "location":         lead.get("location", ""),
                "score":            lead.get("score", 0),
                "score_reason":     lead.get("score_reason", ""),
                "status":           "New",
            })
            if cid:
                add_to_blacklist(cid, name)
            saved += 1
            yield _evt("success", f"Saved [{saved}/{found_count}]: {name} → Notion + blacklisted")
        except Exception as se:
            yield _evt("error", f"Notion save failed for {name}: {str(se)[:150]}")

    elapsed    = int((datetime.now() - start_ts).total_seconds())
    mins, secs = elapsed // 60, elapsed % 60
    new_bl     = blacklist_size()

    yield _evt("complete",
        f"Done! {saved} leads saved  |  {channels_scanned} channels scanned  |  "
        f"{blacklist_hits} skipped by blacklist  |  {new_bl} total in blacklist  |  {mins}m {secs}s",
        {
            "leads_found":      saved,
            "channels_scanned": channels_scanned,
            "time_seconds":     elapsed,
            "niche":            niche_key,
            "location":         location_key,
        },
    )
