import os
import logging
from typing import List, Dict, Optional, Tuple

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

_OUTLINE_COLOR = (0, 0, 0, 255)
_BG_COLOR = (0, 0, 0, 175)
_HOOK_FONT_SIZE = 70
_NAME_FONT_SIZE = 34


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
            files = sorted(videos[0]["video_files"], key=lambda x: x.get("width", 0) or 0, reverse=True)
            for vf in files:
                if (vf.get("width") or 0) >= 720:
                    logger.info(f"Pexels video: '{kw}'")
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
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


# ── Video resize ──────────────────────────────────────────────────────────────

def _resize_to_portrait(clip: VideoFileClip) -> VideoFileClip:
    w, h = clip.size
    scale = max(VIDEO_WIDTH / w, VIDEO_HEIGHT / h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    clip = clip.resize((new_w, new_h))
    x1 = (new_w - VIDEO_WIDTH) / 2
    y1 = (new_h - VIDEO_HEIGHT) / 2
    return moviepy_crop(clip, x1=x1, y1=y1, x2=x1 + VIDEO_WIDTH, y2=y1 + VIDEO_HEIGHT)


# ── Text drawing helpers ──────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.ImageFont:
    if _FONT_PATH:
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _draw_outlined(draw, pos, text, font, fill, outline_width=3):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=_OUTLINE_COLOR)
    draw.text((x, y), text, font=font, fill=fill)


# ── Caption image ─────────────────────────────────────────────────────────────

def _create_caption_image(
    text: str,
    color: Tuple = (255, 230, 0, 255),
    char_name: str = "",
    emoji: str = "",
) -> np.ndarray:
    pad_x, pad_y, radius = 30, 14, 18
    cap_font = _load_font(CAPTION_FONT_SIZE)
    name_font = _load_font(_NAME_FONT_SIZE)

    img_h = 210
    img = Image.new("RGBA", (VIDEO_WIDTH, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Character name tag (small, above) — only for non-narrator
    name_h = 0
    if char_name and char_name != "NARRATOR" and emoji:
        name_text = f"{emoji} {char_name}"
        nb = draw.textbbox((0, 0), name_text, font=name_font)
        nw, nh = nb[2] - nb[0], nb[3] - nb[1]
        nx = (VIDEO_WIDTH - nw) // 2
        draw.text((nx, 8), name_text, font=name_font, fill=color)
        name_h = nh + 12

    # Main caption text
    bbox = draw.textbbox((0, 0), text, font=cap_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Wrap if too wide
    if tw > VIDEO_WIDTH - 60:
        words = text.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        b1 = draw.textbbox((0, 0), line1, font=cap_font)
        b2 = draw.textbbox((0, 0), line2, font=cap_font)
        tw = max(b1[2] - b1[0], b2[2] - b2[0])
        th = (b1[3] - b1[1]) + (b2[3] - b2[1]) + 6
        x = (VIDEO_WIDTH - tw) // 2
        y = name_h + 10
        draw.rounded_rectangle([x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y], radius=radius, fill=_BG_COLOR)
        _draw_outlined(draw, (x, y), line1, cap_font, fill=color)
        y2 = y + (b1[3] - b1[1]) + 6
        _draw_outlined(draw, (x, y2), line2, cap_font, fill=color)
    else:
        x = (VIDEO_WIDTH - tw) // 2
        y = name_h + 10
        draw.rounded_rectangle([x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y], radius=radius, fill=_BG_COLOR)
        _draw_outlined(draw, (x, y), text, cap_font, fill=color)

    return np.array(img)


def _create_hook_image(text: str) -> np.ndarray:
    pad_x, pad_y, radius = 36, 18, 22
    font = _load_font(_HOOK_FONT_SIZE)
    img = Image.new("RGBA", (VIDEO_WIDTH, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if tw > VIDEO_WIDTH - 80:
        words = text.split()
        mid = len(words) // 2
        l1, l2 = " ".join(words[:mid]), " ".join(words[mid:])
        b1 = draw.textbbox((0, 0), l1, font=font)
        b2 = draw.textbbox((0, 0), l2, font=font)
        tw = max(b1[2] - b1[0], b2[2] - b2[0])
        th = (b1[3] - b1[1]) + (b2[3] - b2[1]) + 8
        x, y = (VIDEO_WIDTH - tw) // 2, (200 - th) // 2
        draw.rounded_rectangle([x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y], radius=radius, fill=(200, 0, 0, 215))
        _draw_outlined(draw, (x, y), l1, font, (255, 255, 255, 255))
        _draw_outlined(draw, (x, y + b1[3] - b1[1] + 8), l2, font, (255, 255, 255, 255))
    else:
        x, y = (VIDEO_WIDTH - tw) // 2, (200 - th) // 2
        draw.rounded_rectangle([x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y], radius=radius, fill=(200, 0, 0, 215))
        _draw_outlined(draw, (x, y), text, font, (255, 255, 255, 255))
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

        # Slight dark overlay — better caption readability
        overlay = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=[0, 0, 0]).set_opacity(0.3).set_duration(duration)

        # Caption clips — each with its character's color
        caption_clips = []
        for cap in captions:
            start = cap["start"]
            end = min(cap.get("end", start + 2), duration)
            if start >= end:
                continue
            color = tuple(cap.get("color", (255, 230, 0, 255)))
            char_name = cap.get("char", "")
            emoji = cap.get("emoji", "")
            img = _create_caption_image(cap["text"], color=color, char_name=char_name, emoji=emoji)
            clip = (
                ImageClip(img, ismask=False)
                .set_start(start)
                .set_end(end)
                .set_position((0, CAPTION_Y_POSITION))
            )
            caption_clips.append(clip)

        # Hook text at top (red bg, white text) for first 3 sec
        if hook_text:
            hook_clip = (
                ImageClip(_create_hook_image(hook_text), ismask=False)
                .set_start(0)
                .set_end(min(3.0, duration))
                .set_position((0, 100))
            )
            caption_clips.insert(0, hook_clip)

        final = CompositeVideoClip([video, overlay] + caption_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
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


# ── Scene image helpers ───────────────────────────────────────────────────────

def _load_scene_pil(img_path: str) -> Image.Image:
    """Load scene image, upscale slightly for Ken Burns zoom headroom."""
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    # Scale to 120% so zoom-in doesn't reveal edges
    scale = max(VIDEO_WIDTH * 1.20 / w, VIDEO_HEIGHT * 1.20 / h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    return pil_img.resize((new_w, new_h), Image.LANCZOS)


def _make_ken_burns_clip(img_path: str, duration: float, direction: int = 0) -> Optional[object]:
    """
    Create a Ken Burns animated clip from a single image.
    Applies slow zoom-in or pan so the character appears to move.
    direction: 0=zoom-in-center, 1=pan-left-to-right, 2=pan-right-to-left, 3=zoom-out
    """
    try:
        pil_img = _load_scene_pil(img_path)
        big_w, big_h = pil_img.size
        img_arr = np.array(pil_img)
        fps = VIDEO_FPS
        total_frames = max(1, int(duration * fps))

        # Define start/end crop rectangles (x1,y1,x2,y2) in big image coords
        cx = (big_w - VIDEO_WIDTH) / 2
        cy = (big_h - VIDEO_HEIGHT) / 2

        if direction == 0:   # zoom in toward center
            s = (cx, cy, cx + VIDEO_WIDTH, cy + VIDEO_HEIGHT)
            zoom = 0.06
            e = (cx + VIDEO_WIDTH * zoom / 2, cy + VIDEO_HEIGHT * zoom / 2,
                 cx + VIDEO_WIDTH * (1 - zoom / 2), cy + VIDEO_HEIGHT * (1 - zoom / 2))
        elif direction == 1:  # pan left → right
            margin = min(big_w - VIDEO_WIDTH, int(VIDEO_WIDTH * 0.08))
            s = (0, cy, VIDEO_WIDTH, cy + VIDEO_HEIGHT)
            e = (margin, cy, margin + VIDEO_WIDTH, cy + VIDEO_HEIGHT)
        elif direction == 2:  # pan right → left
            margin = min(big_w - VIDEO_WIDTH, int(VIDEO_WIDTH * 0.08))
            s = (margin, cy, margin + VIDEO_WIDTH, cy + VIDEO_HEIGHT)
            e = (0, cy, VIDEO_WIDTH, cy + VIDEO_HEIGHT)
        else:                 # zoom out from center
            zoom = 0.06
            s = (cx + VIDEO_WIDTH * zoom / 2, cy + VIDEO_HEIGHT * zoom / 2,
                 cx + VIDEO_WIDTH * (1 - zoom / 2), cy + VIDEO_HEIGHT * (1 - zoom / 2))
            e = (cx, cy, cx + VIDEO_WIDTH, cy + VIDEO_HEIGHT)

        def make_frame(t):
            progress = t / duration if duration > 0 else 0
            x1 = s[0] + (e[0] - s[0]) * progress
            y1 = s[1] + (e[1] - s[1]) * progress
            x2 = s[2] + (e[2] - s[2]) * progress
            y2 = s[3] + (e[3] - s[3]) * progress
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            # Clamp
            x1 = max(0, min(x1, big_w - 1))
            y1 = max(0, min(y1, big_h - 1))
            x2 = max(x1 + 1, min(x2, big_w))
            y2 = max(y1 + 1, min(y2, big_h))
            crop = img_arr[y1:y2, x1:x2]
            # Resize crop back to VIDEO_WIDTH x VIDEO_HEIGHT
            from PIL import Image as PImage
            resized = PImage.fromarray(crop).resize((VIDEO_WIDTH, VIDEO_HEIGHT), PImage.LANCZOS)
            return np.array(resized)

        from moviepy.editor import VideoClip
        clip = VideoClip(make_frame, duration=duration)
        return clip
    except Exception as e:
        logger.warning(f"Ken Burns failed for {img_path}: {e}")
        return None


# ── Scene-slideshow video build (with Ken Burns animation) ────────────────────

def build_video_from_scenes(
    scene_image_paths: List[str],
    audio_path: str,
    captions: List[Dict],
    output_path: str,
    hook_text: str = "",
) -> bool:
    """
    Build a YouTube Short: each scene image gets a Ken Burns animated clip
    (slow zoom / pan), giving the illusion of camera movement.
    """
    if not scene_image_paths:
        logger.error("No scene images provided")
        return False

    audio = final = None
    open_clips = []

    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        n = len(scene_image_paths)
        slice_dur = duration / n

        bg_clips = []
        directions = [0, 1, 2, 3, 0]  # alternate directions per scene
        for i, img_path in enumerate(scene_image_paths):
            direction = directions[i % len(directions)]
            clip = _make_ken_burns_clip(img_path, slice_dur, direction=direction)
            if clip is None:
                continue
            clip = clip.set_start(i * slice_dur)
            bg_clips.append(clip)
            open_clips.append(clip)

        if not bg_clips:
            logger.error("All scene images failed to load")
            return False

        # Dark overlay — readability
        overlay = (
            ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=[0, 0, 0])
            .set_opacity(0.28)
            .set_duration(duration)
        )

        # Caption clips (per character color)
        caption_clips = []
        for cap in captions:
            start = cap["start"]
            end = min(cap.get("end", start + 2), duration)
            if start >= end:
                continue
            color = tuple(cap.get("color", (255, 230, 0, 255)))
            char_name = cap.get("char", "")
            emoji = cap.get("emoji", "")
            img = _create_caption_image(cap["text"], color=color, char_name=char_name, emoji=emoji)
            clip = (
                ImageClip(img, ismask=False)
                .set_start(start)
                .set_end(end)
                .set_position((0, CAPTION_Y_POSITION))
            )
            caption_clips.append(clip)
            open_clips.append(clip)

        # Hook text (red pill, top) for first 3.5 sec
        if hook_text:
            hook_clip = (
                ImageClip(_create_hook_image(hook_text), ismask=False)
                .set_start(0)
                .set_end(min(3.5, duration))
                .set_position((0, 100))
            )
            caption_clips.insert(0, hook_clip)
            open_clips.append(hook_clip)

        final = CompositeVideoClip(
            bg_clips + [overlay] + caption_clips,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        )
        final = final.set_audio(audio)
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
        logger.info(f"Scene slideshow video built: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Scene video build failed: {e}", exc_info=True)
        return False

    finally:
        for c in open_clips:
            try: c.close()
            except Exception: pass
        if audio:
            try: audio.close()
            except Exception: pass
        if final:
            try: final.close()
            except Exception: pass
