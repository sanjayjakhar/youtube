import random
import logging
import requests

logger = logging.getLogger(__name__)


def _get_google_trends() -> list:
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        df = pt.trending_searches(pn="united_states")
        return df[0].tolist()[:15]
    except Exception as e:
        logger.warning(f"Google Trends unavailable: {e}")
        return []


def _get_reddit_trending() -> list:
    try:
        headers = {"User-Agent": "YoutubeShorts-Agent/1.0"}
        resp = requests.get(
            "https://www.reddit.com/r/popular.json?limit=20",
            headers=headers,
            timeout=12,
        )
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
        return [p["data"]["title"] for p in posts]
    except Exception as e:
        logger.warning(f"Reddit trending unavailable: {e}")
        return []


def _get_hackernews_trending() -> list:
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10,
        )
        ids = resp.json()[:8]
        titles = []
        for story_id in ids:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=8,
            ).json()
            if item and "title" in item:
                titles.append(item["title"])
        return titles
    except Exception as e:
        logger.warning(f"HackerNews unavailable: {e}")
        return []


_FALLBACK_TOPICS = [
    "amazing deep sea creatures",
    "surprising historical facts",
    "incredible space discoveries",
    "mind-blowing animal intelligence",
    "strange but true science facts",
    "unbelievable world records",
    "fascinating human body facts",
    "mysterious ancient civilizations",
]


def get_trending_topics() -> list:
    google = _get_google_trends()
    reddit = _get_reddit_trending()
    hn = _get_hackernews_trending()

    combined = google[:8] + reddit[:8] + hn[:6]

    if not combined:
        logger.warning("All trend sources failed, using fallback topics")
        return random.sample(_FALLBACK_TOPICS, k=min(5, len(_FALLBACK_TOPICS)))

    random.shuffle(combined)
    return combined[:20]
