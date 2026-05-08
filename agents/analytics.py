import json
import logging
import datetime
import random
from typing import Optional

logger = logging.getLogger(__name__)

_HISTORY_FILE = None
_WEIGHTS_FILE = None


def _paths():
    global _HISTORY_FILE, _WEIGHTS_FILE
    if _HISTORY_FILE is None:
        from config import BASE_DIR
        _HISTORY_FILE = BASE_DIR / "video_history.json"
        _WEIGHTS_FILE = BASE_DIR / "category_weights.json"
    return _HISTORY_FILE, _WEIGHTS_FILE


def _load_history() -> list:
    h, _ = _paths()
    try:
        return json.loads(h.read_text(encoding="utf-8")) if h.exists() else []
    except Exception:
        return []


def _save_history(history: list):
    h, _ = _paths()
    h.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_weights() -> dict:
    from config import CONTENT_CATEGORIES
    _, w = _paths()
    try:
        if w.exists():
            data = json.loads(w.read_text(encoding="utf-8"))
            for cat in CONTENT_CATEGORIES:
                if cat not in data:
                    data[cat] = 1.0
            return data
    except Exception:
        pass
    return {cat: 1.0 for cat in CONTENT_CATEGORIES}


def _save_weights(weights: dict):
    _, w = _paths()
    w.write_text(json.dumps(weights, indent=2, ensure_ascii=False), encoding="utf-8")


def add_video_to_history(video_id: str, category: str, title: str):
    history = _load_history()
    history.append({
        "video_id": video_id,
        "category": category,
        "title": title,
        "upload_date": datetime.datetime.now().isoformat(),
        "views": 0,
        "likes": 0,
        "last_updated": None,
    })
    _save_history(history)
    logger.info(f"History mein save: {video_id} | {title[:40]}")


def should_update_stats() -> bool:
    history = _load_history()
    if not history:
        return False
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    for v in history:
        lu = v.get("last_updated")
        if lu is None:
            return True
        try:
            if datetime.datetime.fromisoformat(lu) < week_ago:
                return True
        except Exception:
            return True
    return False


def update_video_stats() -> Optional[dict]:
    """YouTube se latest views/likes fetch karo aur category weights update karo."""
    from config import CONTENT_CATEGORIES
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file("token.json")
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        youtube = build("youtube", "v3", credentials=creds)

        history = _load_history()
        video_ids = [v["video_id"] for v in history if v.get("video_id")]
        if not video_ids:
            return None

        stats_map = {}
        for i in range(0, len(video_ids), 50):
            resp = youtube.videos().list(
                part="statistics", id=",".join(video_ids[i:i+50])
            ).execute()
            for item in resp.get("items", []):
                stats_map[item["id"]] = item.get("statistics", {})

        now = datetime.datetime.now().isoformat()
        for video in history:
            s = stats_map.get(video.get("video_id", ""), {})
            if s:
                video["views"] = int(s.get("viewCount", 0))
                video["likes"] = int(s.get("likeCount", 0))
                video["last_updated"] = now

        _save_history(history)

        # Compute per-category average engagement score
        # Likes count 15x more than views (strong engagement signal)
        cat_scores: dict = {cat: [] for cat in CONTENT_CATEGORIES}
        for video in history:
            cat = video.get("category", "")
            if cat in cat_scores:
                cat_scores[cat].append(video["views"] + video["likes"] * 15)

        weights = {}
        for cat in CONTENT_CATEGORIES:
            scores = cat_scores.get(cat, [])
            weights[cat] = max(0.3, sum(scores) / len(scores)) if scores else 1.0

        # Normalize so best category = 1.0
        max_w = max(weights.values()) or 1
        weights = {k: round(v / max_w, 4) for k, v in weights.items()}

        _save_weights(weights)

        logger.info("Category weights update ho gaye (views+likes se):")
        for cat, w in sorted(weights.items(), key=lambda x: -x[1]):
            bar = "█" * int(w * 10)
            logger.info(f"  {w:.2f} {bar:<10} {cat[:50]}")

        return weights

    except Exception as e:
        logger.warning(f"Analytics update fail (pipeline continue karega): {e}")
        return None


def pick_weighted_category() -> str:
    """Views/likes ke basis pe best category chunna."""
    from config import CONTENT_CATEGORIES
    weights_data = _load_weights()
    categories = list(weights_data.keys())
    weights = [weights_data.get(c, 1.0) for c in categories]
    chosen = random.choices(categories, weights=weights, k=1)[0]
    logger.info(f"Category chosen (weighted random): {chosen[:55]}")
    return chosen
