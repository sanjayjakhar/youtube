import os
import logging
from typing import List, Dict, Optional

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx.crop import crop as moviepy_crop

from config import (
    PEXELS_API_KEY,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    CAPTION_FONT_SIZE,
    CAPTION_Y_POSITION,
)

logger = logging.getLogger(__name__)

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_FONT_PATH: Optional[str] = next((f for f in _FONT_CANDIDATES if os.path.exists(f)), None)

# Caption style — yellow text, black outline, dark pill bg (TikTok/Reels look)
_CAPTION_COLOR = (255, 230, 0, 255)      # Bright yellow
_OUTLINE_COLOR = (0, 0, 0, 255)          # Black outline
_BG_COLOR = (0, 0, 0, 175)              # Semi-dark bg pill

# Hook text style — larger, white, top of screen
_HOOK_COLOR = (255, 255, 255, 255)
_HOOK_FONT_SIZE = 72


# ── Pexels ────────────────────────────────────────────────────────────────────

def search_pexels_video(keywords: List[str]) -> Optional[str]:
    headers = {"Authorization": PEXELS_API_KEY}
    for kw in keywords:
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params={"query": kw, "per_page": 5, "orientation": "portrait", "size": "medium"},
                timeout=15,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                continue
            files = sorted(
                videos[0]["video_files"],
                key=lambda x: x.get("width", 0) or 0,
                reverse=True,
            )
            for vf in files:
                if (vf.get("width") or 0) >= 720:
                    logger.info(f"Pexels video found for '{kw}'")
                    return vf["link"]
            return files[0]["link"]
        except Exception as e:
            logger.warning(f"Pexels '{kw}': {e}")
    return None


def download_video(url: str, output_path: str) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=90)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        logger.info(f"Downloaded: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


# ── Video processing ──────────────────────────────────────────────────────────

def _resize_to_portrait(clip: VideoFileClip) -> VideoFileClip:
    w, h = clip.size
    scale = max(VIDEO_WIDTH / w, VIDEO_HEIGHT / h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    clip = clip.resize((new_w, new_h))
    x1 = (new_w - VIDEO_WIDTH) / 2
    y1 = (new_h - VIDEO_HEIGHT) / 2
    return moviepy_crop(clip, x1=x1, y1=y1, x2=x1 + VIDEO_WIDTH, y2=y1 + VIDEO_HEIGHT)


# ── Caption / hook image creation ─────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.ImageFont:
    if _FONT_PATH:
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _draw_outlined_text(draw, pos, text, font, fill, outline, outline_width=3):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _create_caption_image(text: str) -> np.ndarray:
    pad_x, pad_y, radius = 32, 16, 20
    font = _load_font(CAPTION_FONT_SIZE)

    img = Image.new("RGBA", (VIDEO_WIDTH, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (VIDEO_WIDTH - tw) // 2
    y = (180 - th) // 2

    # Dark pill background
    draw.rounded_rectangle(
        [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y],
        radius=radius,
        fill=_BG_COLOR,
    )
    _draw_outlined_text(draw, (x, y), text, font, fill=_CAPTION_COLOR, outline=_OUTLINE_COLOR)
    return np.array(img)


def _create_hook_image(text: str) -> np.ndarray:
    pad_x, pad_y, radius = 36, 18, 22
    font = _load_font(_HOOK_FONT_SIZE)

    img = Image.new("RGBA", (VIDEO_WIDTH, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Wrap if too wide
    if tw > VIDEO_WIDTH - 80:
        words = text.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        b1 = draw.textbbox((0, 0), line1, font=font)
        b2 = draw.textbbox((0, 0), line2, font=font)
        tw = max(b1[2] - b1[0], b2[2] - b2[0])
        th = (b1[3] - b1[1]) + (b2[3] - b2[1]) + 8
        x = (VIDEO_WIDTH - tw) // 2
        y = (200 - th) // 2
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y],
            radius=radius, fill=(220, 0, 0, 210),
        )
        _draw_outlined_text(draw, (x, y), line1, font, fill=_HOOK_COLOR, outline=_OUTLINE_COLOR)
        y2 = y + (b1[3] - b1[1]) + 8
        _draw_outlined_text(draw, (x, y2), line2, font, fill=_HOOK_COLOR, outline=_OUTLINE_COLOR)
    else:
        x = (VIDEO_WIDTH - tw) // 2
        y = (200 - th) // 2
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y],
            radius=radius, fill=(220, 0, 0, 210),
        )
        _draw_outlined_text(draw, (x, y), text, font, fill=_HOOK_COLOR, outline=_OUTLINE_COLOR)

    return np.array(img)


# ── Main build ────────────────────────────────────────────────────────────────

def build_video(
    raw_video_path: str,
    audio_path: str,
    captions: List[Dict],
    output_path: str,
    hook_text: str = "",
) -> bool:
    audio = video = final = None
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        video = VideoFileClip(raw_video_path, audio=False)
        video = _resize_to_portrait(video)

        if video.duration < duration:
            loops = int(duration / video.duration) + 2
            video = concatenate_videoclips([video] * loops)

        video = video.subclip(0, duration).set_audio(audio)

        # Subtle dark overlay — improves caption readability
        overlay = (
            ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=[0, 0, 0])
            .set_opacity(0.28)
            .set_duration(duration)
        )

        # Caption clips (yellow)
        caption_clips = []
        for cap in captions:
            start, end = cap["start"], min(cap["end"], duration)
            if start >= end:
                continue
            clip = (
                ImageClip(_create_caption_image(cap["text"]), ismask=False)
                .set_start(start)
                .set_end(end)
                .set_position((0, CAPTION_Y_POSITION))
            )
            caption_clips.append(clip)

        # Hook text at top for first 3 seconds (red bg, white text)
        if hook_text:
            hook_dur = min(3.0, duration)
            hook_clip = (
                ImageClip(_create_hook_image(hook_text), ismask=False)
                .set_start(0)
                .set_end(hook_dur)
                .set_position((0, 100))
            )
            caption_clips.insert(0, hook_clip)

        final = CompositeVideoClip(
            [video, overlay] + caption_clips,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        )
        final.write_videofile(
            output_path,
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=output_path + ".temp.aac",
            remove_temp=True,
            logger=None,
            threads=4,
        )
        logger.info(f"Video built: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        return False

    finally:
        for obj in [audio, video, final]:
            if obj:
                try:
                    obj.close()
                except Exception:
                    pass
