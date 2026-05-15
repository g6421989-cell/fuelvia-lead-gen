# ============================================================
# YOUTUBE ENRICHER - Fetch Video Data (Quota-Efficient)
# ============================================================
# Uses playlistItems.list() = 1 unit  (NOT search().list() = 100 units)
# Per channel cost: ~3 units total
#   1 unit  - playlistItems.list  (get 5 recent video IDs)
#   1 unit  - videos.list         (get stats + snippets for those IDs)
#   0 units - days_since_video calculated from returned dates (no extra call)
# ============================================================

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


def get_videos_for_channel(
    youtube,
    channel_id: str,
    uploads_playlist_id: str = None,
    max_videos: int = 5,
) -> List[Dict]:
    """
    Fetch the last N videos for a channel.

    Prefers uploads_playlist_id (1 unit) over search fallback (100 units).
    Always pass uploads_playlist_id when available.

    Returns list of dicts:
        title, description, view_count, like_count,
        comment_count, published_at, video_id
    """
    videos = []

    # ── Fast path: playlistItems (1 unit) ────────────────────
    if uploads_playlist_id:
        try:
            pl_resp = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=max_videos,
            ).execute()

            items = pl_resp.get("items", [])
            video_ids = [
                it["snippet"]["resourceId"]["videoId"]
                for it in items
                if it.get("snippet", {}).get("resourceId", {}).get("kind") == "youtube#video"
            ]

            if video_ids:
                stats_resp = youtube.videos().list(
                    part="statistics,snippet",
                    id=",".join(video_ids),
                ).execute()

                for item in stats_resp.get("items", []):
                    snippet = item.get("snippet", {})
                    stats   = item.get("statistics", {})
                    videos.append({
                        "title":         snippet.get("title", ""),
                        "description":   snippet.get("description", ""),
                        "view_count":    int(stats.get("viewCount", 0)),
                        "like_count":    int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "published_at":  snippet.get("publishedAt", ""),
                        "video_id":      item.get("id", ""),
                    })

            return videos

        except Exception as e:
            # If this key is also exhausted, bubble the error up so the
            # caller can rotate to the next API key
            raise

    # ── Slow fallback: search (100 units) — avoid if possible ─
    search_resp = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        maxResults=max_videos,
        type="video",
    ).execute()

    items = search_resp.get("items", [])
    video_ids = [it["id"]["videoId"] for it in items]

    if not video_ids:
        return videos

    stats_resp = youtube.videos().list(
        part="statistics,snippet",
        id=",".join(video_ids),
    ).execute()

    for item in stats_resp.get("items", []):
        snippet = item.get("snippet", {})
        stats   = item.get("statistics", {})
        videos.append({
            "title":         snippet.get("title", ""),
            "description":   snippet.get("description", ""),
            "view_count":    int(stats.get("viewCount", 0)),
            "like_count":    int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "published_at":  snippet.get("publishedAt", ""),
            "video_id":      item.get("id", ""),
        })

    return videos


def days_since_last_video(videos_data: List[Dict]) -> int:
    """
    Calculate days since the most recent video from already-fetched data.
    Costs 0 extra API units.
    Returns 999 if no videos or dates available.
    """
    if not videos_data:
        return 999

    now = datetime.now(timezone.utc)
    earliest = 999

    for v in videos_data:
        date_str = v.get("published_at", "")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            delta = (now - dt).days
            if delta < earliest:
                earliest = delta
        except Exception:
            continue

    return earliest
