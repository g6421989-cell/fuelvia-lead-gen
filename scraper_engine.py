# ============================================================
# SCRAPER ENGINE v4 — Fresh Leads Every Run
# ============================================================
# RULES:
# 1. Hard limit 30 max (enforced in API)
# 2. Stop at exact target — not before, not after
# 3. One keyword-location combo at a time
# 4. Break ALL loops when target is reached
# 5. Check email BEFORE fetching videos (save API quota)
# 6. Live log shows "Found X of Y"
# 7. Graceful exhaustion if all combos searched
#
# v4 NEW — 5 FRESH-LEAD SOLUTIONS:
# 1. Page token persistence  — resumes from last page token per query
# 2. City drilling           — appends city names for local creator pools
# 3. Date filter             — publishedAfter to find recently active channels
# 4. Niche video suffixes    — title-style queries surface different creators
# 5. Smart keyword rotation  — Claude avoids already-used keywords
# ============================================================

import re
import time
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build

from config import (
    NICHE_OPTIONS, NICHE_SEARCH_TERMS,
    LOCATION_OPTIONS, SUBSCRIBER_RANGES,
    CITY_DRILL_OPTIONS, VIDEO_SEARCH_SUFFIXES, FRESHNESS_OPTIONS,
)
import settings_store
from notion_manager import NotionManager


def _yt_keys():
    """Read YouTube API keys LIVE from settings store (UI-editable, no restart)."""
    return settings_store.get_list("YOUTUBE_API_KEYS")
from youtube_enricher import get_videos_for_channel, days_since_last_video
from channel_qualifier import qualify_channel, extract_email_from_all_sources
from channel_blacklist import is_blacklisted, add_to_blacklist, blacklist_size
from claude_helpers import generate_keyword_variations
from search_tokens import (
    get_token, save_token,
    get_used_keywords, save_used_keywords,
)

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
    keys = _yt_keys()
    if not keys:
        raise ValueError("No YouTube API keys configured — add them in Settings.")
    key = keys[api_index % len(keys)]
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


def _video_search_channel_ids(
    youtube,
    query: str,
    max_pages: int = 5,
    recency_days: int = None,
) -> list:
    """
    Search YouTube VIDEOS for a query and return unique channel IDs.

    Video search surfaces a completely different pool of creators than
    channel search — typically smaller, niche, less optimised for
    discovery — which is exactly our target audience.

    recency_days: if set, only return videos uploaded in the last N days.
                  This finds channels that just became active / just crossed
                  the subscriber threshold — brand new to any scraper.
                  Use 30 for "recently active", 90 for broader freshness.

    Returns an ordered list of channel IDs (deduped internally).
    Cost: 100 quota units per page (same as channel search).
    """
    channel_ids = []
    seen        = set()
    next_page   = None

    published_after = None
    if recency_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=recency_days)
        published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    for _ in range(max_pages):
        try:
            params = {
                "part":             "snippet",
                "q":                query,
                "type":             "video",
                "maxResults":       50,
                "relevanceLanguage": "en",
                "order":            "date",   # newest uploads first = freshest channels
            }
            if published_after:
                params["publishedAfter"] = published_after
            if next_page:
                params["pageToken"] = next_page

            resp  = youtube.search().list(**params).execute()
            items = resp.get("items", [])
            if not items:
                break

            for item in items:
                cid = (item.get("snippet") or {}).get("channelId")
                if cid and cid not in seen:
                    seen.add(cid)
                    channel_ids.append(cid)

            next_page = resp.get("nextPageToken")
            if not next_page:
                break
            time.sleep(0.2)

        except Exception as e:
            if "quotaExceeded" in str(e) or "403" in str(e):
                pass  # caller handles quota rotation
            break

    return channel_ids


def _process_channel(
    youtube, api_index, notion,
    cid, seen_ids, blacklist_hits_ref,
    sub_min, sub_max,
    niche_key, location_key, keyword, loc,
    target_leads, qualified,
    channels_scanned_ref,
):
    """
    Attempt to qualify one channel ID.

    Returns a tuple: (event_list, new_api_index, incremented_blacklist_hits)
    so the caller can yield events and update counters without managing
    the internals of qualification.
    """
    events = []

    # ── In-run dedup ──────────────────────────────────────────
    if cid in seen_ids:
        return events, api_index, blacklist_hits_ref[0]
    seen_ids.add(cid)

    # ── Permanent blacklist (zero API cost) ───────────────────
    if is_blacklisted(cid):
        blacklist_hits_ref[0] += 1
        return events, api_index, blacklist_hits_ref[0]

    # ── Fetch channel details ─────────────────────────────────
    details = _get_channel(youtube, cid)
    if not details:
        return events, api_index, blacklist_hits_ref[0]

    subs = details["subscriber_count"]
    if subs < sub_min or (sub_max and subs > sub_max):
        return events, api_index, blacklist_hits_ref[0]

    channels_scanned_ref[0] += 1
    name   = details["channel_name"]
    subs_k = f"{subs/1000:.1f}K" if subs >= 1000 else str(subs)

    events.append(_evt("info", f"  Scanning [{channels_scanned_ref[0]}]: {name} ({subs_k} subs)"))

    # ── RULE 5: Email check FIRST (description only, saves quota) ──
    early_email = extract_email_from_all_sources(
        details.get("description", ""),
        [],  # No videos yet — just check description
    )
    if not early_email:
        events.append(_evt("info", f"    Skip {name}: no email in description"))
        return events, api_index, blacklist_hits_ref[0]

    # ── Fetch video data ──────────────────────────────────────
    videos = []
    for _attempt in range(len(_yt_keys())):
        try:
            videos = get_videos_for_channel(
                youtube, cid,
                uploads_playlist_id=details.get("uploads_playlist_id"),
                max_videos=5,
            )
            break
        except Exception as ve:
            if "quotaExceeded" in str(ve) or "403" in str(ve):
                api_index = (api_index + 1) % len(_yt_keys())
                youtube, _ = _get_youtube(api_index)
                events.append(_evt("warning", f"Video API quota — rotated to key #{api_index + 1}"))
            else:
                events.append(_evt("error", f"Video fetch error ({name}): {str(ve)[:120]}"))
                break

    days = days_since_last_video(videos)
    details.update({
        "days_since_last_video": days,
        "videos_data":           videos,
        "niche":                 keyword,
        "location":              loc,
    })

    # ── Qualification ─────────────────────────────────────────
    result = qualify_channel(details, videos, days)

    if not result["qualified"]:
        events.append(_evt("warning", f"    Skip {name}: {result['reason']}"))
        return events, api_index, blacklist_hits_ref[0]

    # ── Notion duplicate check ────────────────────────────────
    try:
        is_dup, _ = notion.check_duplicate(result["email"])
        if is_dup:
            events.append(_evt("warning", f"    Skip {name}: {result['email']} already in database"))
            add_to_blacklist(cid, name)
            return events, api_index, blacklist_hits_ref[0]
    except Exception as de:
        events.append(_evt("error", f"Notion duplicate check failed ({name}): {str(de)[:100]}"))
        return events, api_index, blacklist_hits_ref[0]

    # ── QUALIFIED ✓ ───────────────────────────────────────────
    details["email"]        = result["email"]
    details["score"]        = result["score"]
    details["score_reason"] = result["reason"]
    qualified.append(details)

    found = len(qualified)
    events.append(_evt(
        "success",
        f"Found {found} of {target_leads} requested leads — {name}",
        {"channel": name, "email": result["email"], "score": result["score"]},
    ))

    return events, api_index, blacklist_hits_ref[0]


# ── Main generator ────────────────────────────────────────

def scrape_leads(
    niche_key:        str,
    location_key:     str,
    sub_range_key:    str,
    max_leads:        int = None,
    date_filter_days: int = None,
    city_drill_key:   str = None,
    use_fresh_keywords: bool = True,
):
    """
    Generator — yields event dicts until exactly max_leads are found.

    v4 parameters:
      date_filter_days  — only surface channels that uploaded in last N days (None = any time)
      city_drill_key    — key from CITY_DRILL_OPTIONS to append city names to queries
      use_fresh_keywords — tell Claude to avoid already-used keywords (default True)

    Discovery strategy per keyword-location pair:
      Phase A: YouTube channel search  (popularity-biased pool, paginated from last token)
      Phase B: YouTube VIDEO search    (different creator pool — title-style queries)
    """
    # ── Guard: API keys must be configured ───────────────────────────
    if not _yt_keys():
        yield _evt("error",
            "No YouTube API keys found. "
            "Add them in Settings, then start the scrape again."
        )
        yield _evt("complete", "Scrape aborted — no API keys", {
            "leads_found": 0, "channels_scanned": 0,
            "time_seconds": 0, "niche": niche_key,
        })
        return

    target_leads = max_leads if max_leads and max_leads > 0 else DEFAULT_TARGET_LEADS

    start_ts  = datetime.now()
    keywords  = list(NICHE_SEARCH_TERMS.get(niche_key, [niche_key]))
    loc_list  = LOCATION_OPTIONS.get(location_key, [""])
    sub_min, sub_max = SUBSCRIBER_RANGES.get(sub_range_key, (1000, 20000))

    # ── Solution 3: Date filter (publishedAfter) ──────────────────────
    published_after = None
    if date_filter_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=date_filter_days)
        published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Solution 2: City drilling ─────────────────────────────────────
    city_list = []
    if city_drill_key and city_drill_key in CITY_DRILL_OPTIONS:
        city_list = CITY_DRILL_OPTIONS[city_drill_key]

    bl_size = blacklist_size()
    yield _evt("info", f"Niche: {niche_key}  |  Location: {location_key}")
    yield _evt("info", f"Subscriber range: {sub_range_key}")
    yield _evt("info", f"Blacklist: {bl_size} channels permanently skipped")
    if published_after:
        yield _evt("info", f"Date filter: last {date_filter_days} days only → freshest channels")
    if city_list:
        yield _evt("info", f"City drilling: {len(city_list)} cities → {len(city_list) * len(keywords)} extra query combos")

    # ── Solution 5: Smart keyword rotation ───────────────────────────
    # Pass already-used keywords to Claude so it generates NEW variations
    used_kws = get_used_keywords(niche_key) if use_fresh_keywords else []
    yield _evt("info", f"Generating keyword variations with Claude… ({len(used_kws)} already used → will avoid)")
    variations = generate_keyword_variations(niche_key, keywords, used_keywords=used_kws)
    if variations:
        keywords = keywords + variations
        yield _evt("success",
            f"Claude added {len(variations)} fresh keyword variations → {len(keywords)} total"
        )
    else:
        yield _evt("info", f"No variations generated (Claude unavailable) — using {len(keywords)} base keywords")

    # Save all keywords as used so next run gets different ones
    if use_fresh_keywords:
        save_used_keywords(niche_key, keywords)

    # ── Solution 4: Niche video search suffixes ───────────────────────
    niche_suffixes = VIDEO_SEARCH_SUFFIXES.get(niche_key, VIDEO_SEARCH_SUFFIXES.get("other", []))

    yield _evt("info", f"Keywords ({len(keywords)}): {', '.join(keywords[:5])}{'…' if len(keywords)>5 else ''}")
    yield _evt("info", f"Target: exactly {target_leads} leads with valid emails")
    yield _evt("info", f"Strategy: Channel search + Video search (dual-source) + {len(niche_suffixes)} title-style queries")

    api_index = 0
    youtube, api_index = _get_youtube(api_index)
    notion    = NotionManager()

    seen_ids         = set()
    blacklist_hits   = [0]
    qualified        = []
    channels_scanned = [0]
    target_reached   = False

    # Build keyword-location pairs
    # Solution 2: interleave city queries between regular queries
    keyword_location_pairs = []
    for keyword in keywords:
        for loc in loc_list:
            keyword_location_pairs.append((keyword, loc if loc else "Global"))
        # Add city-drilled variants
        for city in city_list:
            keyword_location_pairs.append((f"{keyword} {city}", city))

    yield _evt("info", f"{len(keyword_location_pairs)} keyword-location combinations queued")

    # ══════════════════════════════════════════════════════════════
    # MAIN LOOP — one keyword-location pair at a time
    # ══════════════════════════════════════════════════════════════
    for pair_idx, (keyword, loc) in enumerate(keyword_location_pairs, 1):
        if target_reached:
            break

        query = f"{keyword} {loc}".strip() if loc != "Global" else keyword
        yield _evt("info", f"[{pair_idx}/{len(keyword_location_pairs)}] Searching: '{query}'")

        # ──────────────────────────────────────────────────────────
        # PHASE A: YouTube Channel Search
        # Solution 1: resume from saved page token (not page 1 every time)
        # Solution 3: apply date filter if set
        # ──────────────────────────────────────────────────────────
        # Load saved token — continues from where last run left off
        saved_token = get_token(query, loc)
        next_page   = saved_token
        page_num    = 0
        if saved_token:
            yield _evt("info", f"  Phase A: channel search (resuming from saved page token)…")
        else:
            yield _evt("info", f"  Phase A: channel search (starting from page 1)…")

        while len(qualified) < target_leads and page_num < 15:
            try:
                params = {
                    "part":             "snippet",
                    "q":                query,
                    "type":             "channel",
                    "maxResults":       50,
                    "relevanceLanguage": "en",
                }
                if next_page:
                    params["pageToken"] = next_page
                # Note: publishedAfter is not supported on channel-type search.
                # Date filter (Solution 3) is applied in Phase B video search instead.

                resp  = youtube.search().list(**params).execute()
                items = resp.get("items", [])
                if not items:
                    save_token(query, loc, None)  # reset — exhausted
                    break

            except Exception as e:
                if "quotaExceeded" in str(e) or "403" in str(e):
                    api_index = (api_index + 1) % len(_yt_keys())
                    youtube, api_index = _get_youtube(api_index)
                    yield _evt("warning", f"Search quota — rotated to key #{api_index + 1}/{len(_yt_keys())}")
                    time.sleep(1)
                    continue
                else:
                    yield _evt("error", f"Channel search failed: {str(e)[:160]}")
                    break

            for item in items:
                if len(qualified) >= target_leads:
                    target_reached = True
                    break

                cid = item["snippet"]["channelId"]
                events, api_index, _ = _process_channel(
                    youtube, api_index, notion,
                    cid, seen_ids, blacklist_hits,
                    sub_min, sub_max,
                    niche_key, location_key, keyword, loc,
                    target_leads, qualified,
                    channels_scanned,
                )
                for ev in events:
                    yield ev
                if len(qualified) >= target_leads:
                    target_reached = True
                    break
                time.sleep(0.1)

            if target_reached:
                break
            next_page = resp.get("nextPageToken")
            # Solution 1: save token after each page so next run continues here
            save_token(query, loc, next_page)
            if not next_page:
                break
            page_num += 1
            time.sleep(0.3)

        if target_reached:
            yield _evt("info", f"Target reached in Phase A.")
            break

        # ──────────────────────────────────────────────────────────
        # PHASE B: YouTube Video Search → extract channel IDs
        # YouTube video search surfaces completely different creators
        # than channel search — smaller, niche, less algorithm-favoured
        # Solution 4: niche suffixes produce title-style queries that
        # surface creators who wouldn't appear in channel search at all.
        # ──────────────────────────────────────────────────────────
        if len(qualified) < target_leads:
            yield _evt("info", f"  Phase B: video search (different creator pool)…")

            # Build Phase B query list:
            # - base query (broad relevance)
            # - base query with date filter (freshest channels)
            # - Solution 4: niche-specific title-style suffix queries
            phase_b_queries = []

            # Sweep 1: broad relevance (no recency filter)
            phase_b_queries.append((query, None))

            # Sweep 2: recently uploaded (Solution 3 + fresh channel discovery)
            recency = date_filter_days if date_filter_days else 45
            phase_b_queries.append((query, recency))

            # Solution 4: niche suffixes — title-style queries find completely
            # different creators than a plain niche keyword search
            for suffix in niche_suffixes:
                suffix_query = f"{query} {suffix}"
                phase_b_queries.append((suffix_query, None))
                # Also add a fresh variant of each suffix query
                phase_b_queries.append((suffix_query, recency))

            yield _evt(
                "info",
                f"  Phase B: {len(phase_b_queries)} video queries "
                f"(1 broad + 1 fresh + {len(niche_suffixes)*2} niche-suffix sweeps)"
            )

            # Run all Phase B sweeps, collecting unique channel IDs
            all_video_cids = []
            _seen_v = set()
            for b_query, b_recency in phase_b_queries:
                if len(qualified) >= target_leads:
                    target_reached = True
                    break
                cids = _video_search_channel_ids(
                    youtube, b_query,
                    max_pages=3,
                    recency_days=b_recency,
                )
                for cid in cids:
                    if cid not in _seen_v:
                        _seen_v.add(cid)
                        all_video_cids.append(cid)

            new_cids = [c for c in all_video_cids if c not in seen_ids]
            yield _evt("info", f"  Video search found {len(new_cids)} new unique channels to check")

            for cid in new_cids:
                if len(qualified) >= target_leads:
                    target_reached = True
                    break

                events, api_index, _ = _process_channel(
                    youtube, api_index, notion,
                    cid, seen_ids, blacklist_hits,
                    sub_min, sub_max,
                    niche_key, location_key, keyword, loc,
                    target_leads, qualified,
                    channels_scanned,
                )
                for ev in events:
                    yield ev
                time.sleep(0.1)

            if target_reached:
                yield _evt("info", f"Target reached in Phase B.")
                break

        # ── Progress update after each keyword-location pair ──
        yield _evt(
            "progress",
            f"  Pair {pair_idx}/{len(keyword_location_pairs)} done — {len(qualified)}/{target_leads} leads found",
            {"found": len(qualified), "target": target_leads},
        )

    # ══════════════════════════════════════════════════════════════
    # PHASE 2: SAVE LEADS TO NOTION + BLACKLIST
    # ══════════════════════════════════════════════════════════════
    if not qualified:
        elapsed = int((datetime.now() - start_ts).total_seconds())
        yield _evt("error",
            f"No qualified leads found after scanning {channels_scanned[0]} channels "
            f"({blacklist_hits[0]} skipped by blacklist). "
            f"Try a broader niche, wider subscriber range, or different location.",
        )
        yield _evt("complete", "Search complete — 0 leads found", {
            "leads_found": 0, "channels_scanned": channels_scanned[0],
            "time_seconds": elapsed, "niche": niche_key,
        })
        return

    found_count = len(qualified)
    yield _evt("info", "─" * 50)

    if found_count < target_leads:
        yield _evt("info", f"Search exhausted — found {found_count}/{target_leads} requested. Saving.")
    else:
        yield _evt("info", f"Target reached — {found_count} leads. Saving to Notion + blacklist…")

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
        f"Done! {saved} leads saved  |  {channels_scanned[0]} channels scanned  |  "
        f"{blacklist_hits[0]} skipped by blacklist  |  {new_bl} total in blacklist  |  {mins}m {secs}s",
        {
            "leads_found":      saved,
            "channels_scanned": channels_scanned[0],
            "time_seconds":     elapsed,
            "niche":            niche_key,
            "location":         location_key,
        },
    )
