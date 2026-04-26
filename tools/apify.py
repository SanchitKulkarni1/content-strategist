import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from apify_client import ApifyClient
from dotenv import load_dotenv

from tools.cache import APIFY_TTL, cache_get, cache_set, make_cache_key

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

PROFILE_ACTOR  = "apify/instagram-profile-scraper"
POST_ACTOR     = "apify/instagram-post-scraper"
DEFAULT_POSTS  = 12  # per account

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _parse_profile(raw: dict) -> dict:
    return {
        "username":      raw.get("username"),
        "full_name":     raw.get("fullName"),
        "bio":           raw.get("biography"),
        "followers":     raw.get("followersCount"),
        "following":     raw.get("followsCount"),
        "posts_count":   raw.get("postsCount"),
        "website":       raw.get("externalUrl"),
        "is_verified":   raw.get("verified", False),
        "is_business":   raw.get("isBusinessAccount", False),
        "profile_pic":   raw.get("profilePicUrl"),
    }

def _parse_post(raw: dict) -> dict:
    likes    = raw.get("likesCount", 0) or 0
    comments = raw.get("commentsCount", 0) or 0
    views    = raw.get("videoViewCount")

    # Engagement rate: (likes + comments) / views * 100 for videos
    # (likes + comments) as raw count for images
    engagement_score = round(((likes + comments) / views * 100), 2) if views else (likes + comments)

    return {
        "type":             raw.get("type"),           # Image / Video / Sidecar
        "format":           raw.get("productType"),    # clips = Reel, feed = Image
        "caption":          raw.get("caption"),
        "hashtags":         raw.get("hashtags", []),
        "likes":            likes,
        "comments":         comments,
        "views":            views,
        "engagement_score": engagement_score,
        "timestamp":        raw.get("timestamp"),
        "is_pinned":        raw.get("isPinned", False),
        "collab_tags":      [u["username"] for u in raw.get("taggedUsers", [])],
        "post_url":         raw.get("url"),
    }

# ─────────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────────

def scrape_profiles(usernames: list[str]) -> dict[str, dict]:
    """Returns a dict keyed by username with profile data."""
    logger.info(f"Scraping profiles for: {usernames}")

    run = client.actor(PROFILE_ACTOR).call(
        run_input={"usernames": usernames}
    )

    profiles = {}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        parsed = _parse_profile(item)
        uname  = parsed["username"]
        if uname:
            profiles[uname] = parsed

    logger.info(f"Fetched {len(profiles)} profiles")
    return profiles


def scrape_posts(usernames: list[str], limit: int = DEFAULT_POSTS) -> dict[str, list]:
    """Returns a dict keyed by username with list of parsed posts."""
    logger.info(f"Scraping last {limit} posts for: {usernames}")

    run = client.actor(POST_ACTOR).call(
        run_input={
            "username":    usernames,
            "resultsLimit": limit
        }
    )

    posts: dict[str, list] = {u: [] for u in usernames}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        uname = item.get("ownerUsername")
        if uname in posts:
            posts[uname].append(_parse_post(item))

    for uname, p in posts.items():
        logger.info(f"  {uname}: {len(p)} posts fetched")

    return posts

# ─────────────────────────────────────────────
# MAIN INTELLIGENCE BUILDER
# ─────────────────────────────────────────────

def get_brand_intelligence(
    brand_username: str,
    competitor_usernames: list[str],
    posts_per_account: int = DEFAULT_POSTS
) -> dict:
    """
    Full competitive intelligence payload.
    Returns structured data for brand + all competitors.
    Ready to pass directly into LLM for analysis.
    """
    all_usernames = [brand_username] + competitor_usernames
    date_bucket = datetime.now().strftime("%Y-%m-%d")
    cache_key = make_cache_key(
        "apify_brand_intelligence",
        sorted(all_usernames),
        date_bucket,
    )
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("Apify intelligence cache hit (%s)", date_bucket)
        return cached

    logger.info("Apify intelligence cache miss (%s)", date_bucket)

    with ThreadPoolExecutor(max_workers=2) as executor:
        profiles_future = executor.submit(scrape_profiles, all_usernames)
        posts_future = executor.submit(scrape_posts, all_usernames, posts_per_account)
        profiles = profiles_future.result()
        posts = posts_future.result()

    intelligence = {}
    for uname in all_usernames:
        account_posts = posts.get(uname, [])

        # Aggregate stats
        total_likes    = sum(p["likes"] for p in account_posts)
        total_comments = sum(p["comments"] for p in account_posts)
        total_views    = sum(p["views"] for p in account_posts if p["views"])
        avg_likes      = round(total_likes / len(account_posts), 1) if account_posts else 0
        avg_comments   = round(total_comments / len(account_posts), 1) if account_posts else 0

        # Content type breakdown
        type_counts = {}
        for p in account_posts:
            t = p.get("format") or p.get("type") or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1

        # All hashtags used
        all_hashtags = [tag for p in account_posts for tag in p["hashtags"]]

        # Collab/influencer accounts tagged
        all_collabs = list(set(tag for p in account_posts for tag in p["collab_tags"]))

        intelligence[uname] = {
            "is_brand":    uname == brand_username,
            "profile":     profiles.get(uname, {}),
            "posts":       account_posts,
            "analytics": {
                "total_posts_analyzed": len(account_posts),
                "avg_likes":            avg_likes,
                "avg_comments":         avg_comments,
                "total_views":          total_views,
                "content_type_mix":     type_counts,   # e.g. {"clips": 8, "feed": 4}
                "all_hashtags_used":    all_hashtags,
                "influencer_collabs":   all_collabs,
            }
        }

    cache_set(cache_key, intelligence, APIFY_TTL)
    return intelligence