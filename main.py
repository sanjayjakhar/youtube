import logging
import datetime
from pathlib import Path

from config import OUTPUT_DIR, LOGS_DIR
from agents.trend_finder import get_trending_topics
from agents.script_writer import generate_video_content
from agents.tts_engine import generate_multi_char_tts
from agents.video_builder import search_pexels_video, download_video, build_video, build_video_from_scenes
from agents.image_generator import generate_scene_images
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
    if not category:
        if should_update_stats():
            logger.info("Weekly analytics refresh...")
            update_video_stats()
        category = pick_weighted_category()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / timestamp
    work_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 55)
    logger.info(f"YouTube Shorts Agent — {category[:45]}")
    logger.info("=" * 55)

    # 1. Trending topics
    logger.info("[1/6] Trending topics...")
    topics = get_trending_topics()
    logger.info(f"      {len(topics)} topics mile")

    # 2. Dialogue script generate
    logger.info("[2/6] Multi-character Hindi script generate ho rahi hai...")
    try:
        content = generate_video_content(topics, category)
    except Exception as e:
        logger.error(f"Script fail: {e}")
        return False

    dialogue = content.get("dialogue", [])
    if not dialogue:
        logger.error("Dialogue empty — aborting")
        return False

    (work_dir / "content.txt").write_text(
        f"CATEGORY : {category}\n"
        f"TOPIC    : {content['chosen_topic']}\n"
        f"TITLE    : {content['title']}\n"
        f"HOOK     : {content.get('hook_text', '')}\n\n"
        + "\n".join(f"[{d['char']}]: {d['text']}" for d in dialogue)
        + f"\n\nDESCRIPTION:\n{content['description']}\n\nTAGS: {', '.join(content['tags'])}",
        encoding="utf-8",
    )

    # 3. Multi-character TTS
    logger.info("[3/6] Multi-character voiceover ban rahi hai (RAVI + PRIYA)...")
    audio_path = str(work_dir / "narration.mp3")
    try:
        captions = generate_multi_char_tts(dialogue, audio_path)
    except Exception as e:
        logger.error(f"TTS fail: {e}")
        return False

    logger.info(f"      {len(captions)} caption chunks ready")

    # 4. AI cinematic scene images (Avengers, superheroes, actors in Indian settings)
    logger.info("[4/6] AI cinematic scenes generate ho rahe hain (Pollinations.ai)...")
    scene_images = generate_scene_images(
        category=category,
        chosen_topic=content.get("chosen_topic", ""),
        work_dir=str(work_dir),
        count=5,
    )

    # 5. Build video
    logger.info("[5/6] Video build ho raha hai...")
    final_video_path = str(work_dir / "final_short.mp4")

    video_built = False

    if scene_images:
        logger.info(f"      AI scene slideshow mode: {len(scene_images)} images")
        video_built = build_video_from_scenes(
            scene_image_paths=scene_images,
            audio_path=audio_path,
            captions=captions,
            output_path=final_video_path,
            hook_text=content.get("hook_text", ""),
        )
        if not video_built:
            logger.warning("Scene video failed, trying Pexels fallback...")

    if not video_built:
        logger.info("      Pexels stock footage fallback...")
        raw_video_path = str(work_dir / "raw_footage.mp4")
        keywords = content.get("search_keywords", ["india street"])
        video_url = search_pexels_video(keywords)
        if video_url and download_video(video_url, raw_video_path):
            video_built = build_video(
                raw_video_path,
                audio_path,
                captions,
                final_video_path,
                hook_text=content.get("hook_text", ""),
            )

    if not video_built:
        logger.error("Build fail — both scene and Pexels paths failed")
        return False

    # 6. Upload
    logger.info("[6/6] YouTube pe upload...")
    url = upload_video(
        final_video_path,
        title=content["title"],
        description=content["description"],
        tags=content["tags"],
    )

    if url:
        logger.info(f"SUCCESS ✓  {url}")
        video_id = url.rstrip("/").split("/")[-1]
        add_video_to_history(video_id, category, content["title"])
        (work_dir / "youtube_url.txt").write_text(url, encoding="utf-8")
        return True

    logger.error("Upload fail")
    return False


if __name__ == "__main__":
    run_pipeline()
