import logging
import datetime
import os
from pathlib import Path

from config import OUTPUT_DIR, LOGS_DIR
from agents.trend_finder import get_trending_topics
from agents.script_writer import generate_video_content
from agents.tts_engine import generate_multi_char_tts
from agents.video_builder import search_pexels_video, download_video, build_video, build_video_from_scenes, build_video_from_did_clips
from agents.image_generator import generate_scene_images, generate_character_portrait
from agents.talking_face import generate_talking_clip
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

    # 2. AI scene images — decides which characters appear in this video
    logger.info("[2/6] AI cinematic scenes generate ho rahe hain (Pollinations.ai)...")
    scene_result = generate_scene_images(
        category=category,
        chosen_topic="",      # topic not known yet; images generate first
        work_dir=str(work_dir),
        count=5,
    )
    scene_image_paths = scene_result.get("paths", [])
    char1 = scene_result.get("char1", "HULK")
    char2 = scene_result.get("char2", "REPORTER")
    logger.info(f"      {len(scene_image_paths)} scenes | Characters: {char1} + {char2}")

    # 3. Script — written FOR the characters shown in the images
    logger.info(f"[3/6] {char1} + {char2} ka Hindi script generate ho raha hai...")
    try:
        content = generate_video_content(topics, category, char1=char1, char2=char2)
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
        f"HOOK     : {content.get('hook_text', '')}\n"
        f"CHARS    : {char1} + {char2}\n\n"
        + "\n".join(f"[{d['char']}]: {d['text']}" for d in dialogue)
        + f"\n\nDESCRIPTION:\n{content['description']}\n\nTAGS: {', '.join(content['tags'])}",
        encoding="utf-8",
    )

    # 4. TTS — each character speaks in their own voice
    logger.info(f"[4/6] {char1} + {char2} ki voiceover ban rahi hai...")
    audio_path = str(work_dir / "narration.mp3")
    try:
        captions = generate_multi_char_tts(dialogue, audio_path)
    except Exception as e:
        logger.error(f"TTS fail: {e}")
        return False

    logger.info(f"      {len(captions)} caption chunks ready")

    # 5. D-ID talking face clips — portrait image + per-char audio → lip sync
    did_key = os.getenv("DID_API_KEY", "")
    did_clips = {}  # {"CHAR1": path, "CHAR2": path}

    if did_key:
        logger.info("[5a/6] D-ID talking face generate ho raha hai...")
        char_audio_dir = str(work_dir / "char_audio")
        os.makedirs(char_audio_dir, exist_ok=True)

        for char_name in [char1, char2]:
            char_lines = [cap for cap in captions if cap.get("char") == char_name]
            if not char_lines:
                continue

            # 1. Generate close-up portrait for this character
            portrait_path = generate_character_portrait(
                char_name, str(work_dir), seed=hash(char_name) % 99999
            )
            if not portrait_path:
                logger.warning(f"Portrait failed for {char_name}, skipping D-ID")
                continue

            # 2. Extract just this character's audio lines from full narration
            try:
                from moviepy.editor import AudioFileClip, concatenate_audioclips
                full_audio = AudioFileClip(audio_path)
                segments = []
                for cap in char_lines:
                    s, e = cap["start"], min(cap["end"], full_audio.duration)
                    if e > s:
                        segments.append(full_audio.subclip(s, e))
                if not segments:
                    full_audio.close()
                    continue
                char_audio = concatenate_audioclips(segments)
                char_audio_path = os.path.join(char_audio_dir, f"{char_name}_voice.mp3")
                char_audio.write_audiofile(char_audio_path, fps=44100, logger=None)
                char_audio.close()
                full_audio.close()
                for seg in segments:
                    try: seg.close()
                    except Exception: pass
            except Exception as e:
                logger.warning(f"Per-char audio extraction failed for {char_name}: {e}")
                char_audio_path = audio_path  # fallback to full audio

            # 3. Generate D-ID talking clip
            char_clip_path = os.path.join(char_audio_dir, f"{char_name}_talking.mp4")
            if generate_talking_clip(portrait_path, char_audio_path, char_clip_path, did_key):
                did_clips[char_name] = char_clip_path
                logger.info(f"D-ID clip ready: {char_name}")
            else:
                logger.warning(f"D-ID failed for {char_name}")

    # 5b. Build video
    logger.info("[5/6] Video build ho raha hai...")
    final_video_path = str(work_dir / "final_short.mp4")
    video_built = False

    if did_clips and scene_image_paths:
        logger.info(f"      D-ID talking mode: {list(did_clips.keys())}")
        video_built = build_video_from_did_clips(
            did_clips=did_clips,
            scene_image_paths=scene_image_paths,
            audio_path=audio_path,
            captions=captions,
            output_path=final_video_path,
            hook_text=content.get("hook_text", ""),
        )
        if not video_built:
            logger.warning("D-ID video failed, falling back to Ken Burns...")

    if not video_built and scene_image_paths:
        video_built = build_video_from_scenes(
            scene_image_paths=scene_image_paths,
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
        keywords = content.get("search_keywords", ["superhero india"])
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
