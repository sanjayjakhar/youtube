import logging
import datetime
from pathlib import Path

from config import OUTPUT_DIR, LOGS_DIR
from agents.trend_finder import get_trending_topics
from agents.script_writer import generate_video_content
from agents.tts_engine import generate_tts, group_into_captions
from agents.video_builder import search_pexels_video, download_video, build_video
from agents.uploader import upload_video
from agents.analytics import (
    pick_weighted_category,
    should_update_stats,
    update_video_stats,
    add_video_to_history,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "agent.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run_pipeline(category: str = None) -> bool:
    # Smart category selection: zyada views wali category ko zyada mauka
    if not category:
        if should_update_stats():
            logger.info("Weekly analytics refresh ho rahi hai...")
            update_video_stats()
        category = pick_weighted_category()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / timestamp
    work_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 55)
    logger.info(f"YouTube Shorts Agent — {category[:45]}")
    logger.info("=" * 55)

    # 1. Trending topics
    logger.info("[1/6] Trending topics fetch kar rahe hain...")
    topics = get_trending_topics()
    logger.info(f"      {len(topics)} topics mile")

    # 2. Script generate
    logger.info("[2/6] Hindi script AI se generate ho rahi hai...")
    try:
        content = generate_video_content(topics, category)
    except Exception as e:
        logger.error(f"Script generation fail: {e}")
        return False

    (work_dir / "content.txt").write_text(
        f"CATEGORY: {category}\n"
        f"TOPIC   : {content['chosen_topic']}\n"
        f"TITLE   : {content['title']}\n"
        f"HOOK    : {content.get('hook_text', '')}\n\n"
        f"SCRIPT:\n{content['script']}\n\n"
        f"DESCRIPTION:\n{content['description']}\n\n"
        f"TAGS: {', '.join(content['tags'])}",
        encoding="utf-8",
    )

    # 3. TTS
    logger.info("[3/6] Hindi voiceover ban rahi hai...")
    audio_path = str(work_dir / "narration.mp3")
    try:
        word_timings = generate_tts(content["script"], audio_path)
    except Exception as e:
        logger.error(f"TTS fail: {e}")
        return False

    captions = group_into_captions(word_timings)
    logger.info(f"      {len(word_timings)} words → {len(captions)} caption chunks")

    # 4. Stock footage
    logger.info("[4/6] Pexels se footage dhundh rahe hain...")
    raw_video_path = str(work_dir / "raw_footage.mp4")
    keywords = content.get("search_keywords", ["nature"])
    video_url = search_pexels_video(keywords)

    if not video_url:
        logger.error("Footage nahi mila")
        return False
    if not download_video(video_url, raw_video_path):
        logger.error("Footage download fail")
        return False

    # 5. Build video
    logger.info("[5/6] Video ban raha hai (captions + hook)...")
    final_video_path = str(work_dir / "final_short.mp4")
    if not build_video(
        raw_video_path,
        audio_path,
        captions,
        final_video_path,
        hook_text=content.get("hook_text", ""),
    ):
        logger.error("Video build fail")
        return False

    # 6. Upload
    logger.info("[6/6] YouTube pe upload ho raha hai...")
    url = upload_video(
        final_video_path,
        title=content["title"],
        description=content["description"],
        tags=content["tags"],
    )

    if url:
        logger.info(f"SUCCESS ✓  {url}")
        # Save to analytics history
        video_id = url.rstrip("/").split("/")[-1]
        add_video_to_history(video_id, category, content["title"])
        (work_dir / "youtube_url.txt").write_text(url, encoding="utf-8")
        return True

    logger.error("Upload fail")
    return False


if __name__ == "__main__":
    run_pipeline()
