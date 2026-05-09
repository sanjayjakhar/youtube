import asyncio
import os
import logging
import tempfile
import shutil
from typing import List, Dict, Optional

import numpy as np
import edge_tts
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip

from config import CHARACTERS, CAPTION_CHUNK_SIZE

logger = logging.getLogger(__name__)

GAP_MS = 320  # silence between dialogue lines

# Try importing ElevenLabs engine
try:
    from agents.voice_engine import generate_elevenlabs_audio, check_quota
    _EL_AVAILABLE = True
except ImportError:
    _EL_AVAILABLE = False


def _get_el_key() -> Optional[str]:
    key = os.getenv("ELEVENLABS_API_KEY", "")
    return key if key else None


# ── ElevenLabs segment generation ────────────────────────────────────────────

def _generate_el_segment(text: str, char_name: str, output_path: str, api_key: str) -> List[Dict]:
    """Generate audio via ElevenLabs, return estimated word timings."""
    success = generate_elevenlabs_audio(text, char_name, output_path, api_key)
    if not success:
        return []

    # ElevenLabs doesn't return word timings — estimate from audio duration
    try:
        clip = AudioFileClip(output_path)
        duration = clip.duration
        clip.close()
    except Exception:
        duration = len(text) * 0.065  # rough estimate

    words = text.split()
    if not words:
        return []
    dpw = duration / len(words)
    return [
        {"word": w, "start": i * dpw, "end": (i + 1) * dpw}
        for i, w in enumerate(words)
    ]


# ── edge-tts segment generation (fallback) ───────────────────────────────────

async def _generate_edge_segment(text: str, voice: str, rate: str, output_path: str) -> List[Dict]:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    sentence_timings: List[Dict] = []
    audio_bytes = bytearray()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            start = chunk["offset"] / 10_000_000
            end = (chunk["offset"] + chunk["duration"]) / 10_000_000
            sentence_timings.append({"text": chunk["text"], "start": start, "end": end})

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    word_timings: List[Dict] = []
    for s in sentence_timings:
        words = s["text"].split()
        if not words:
            continue
        dpw = (s["end"] - s["start"]) / len(words)
        for i, w in enumerate(words):
            word_timings.append({
                "word": w,
                "start": s["start"] + i * dpw,
                "end": s["start"] + (i + 1) * dpw,
            })
    return word_timings


# ── Main multi-character TTS ──────────────────────────────────────────────────

def generate_multi_char_tts(dialogue: List[Dict], output_path: str) -> List[Dict]:
    """
    Generate multi-character audio + return per-char timed captions.
    Uses ElevenLabs if API key available, otherwise falls back to edge-tts.
    """
    el_key = _get_el_key() if _EL_AVAILABLE else None
    use_elevenlabs = bool(el_key)

    if use_elevenlabs:
        logger.info("Using ElevenLabs for character voices")
        quota = check_quota(el_key)
        if not quota["ok"]:
            logger.warning("ElevenLabs quota low — falling back to edge-tts")
            use_elevenlabs = False
    else:
        logger.info("Using edge-tts for voices (ElevenLabs key not set)")

    temp_dir = tempfile.mkdtemp()
    try:
        results = []
        for i, line in enumerate(dialogue):
            char_name = line.get("char", "NARRATOR")
            text = line.get("text", "").strip()
            if not text:
                continue
            char_cfg = CHARACTERS.get(char_name, CHARACTERS["NARRATOR"])
            seg_path = os.path.join(temp_dir, f"seg_{i:03d}.mp3")

            if use_elevenlabs:
                word_timings = _generate_el_segment(text, char_name, seg_path, el_key)
                if not word_timings and not os.path.exists(seg_path):
                    # ElevenLabs failed — fall back to edge-tts for this line
                    logger.warning(f"EL failed for line {i}, using edge-tts")
                    word_timings = asyncio.run(
                        _generate_edge_segment(text, char_cfg["voice"], char_cfg["rate"], seg_path)
                    )
            else:
                word_timings = asyncio.run(
                    _generate_edge_segment(text, char_cfg["voice"], char_cfg["rate"], seg_path)
                )

            results.append((line, char_cfg, seg_path, word_timings))

        # Concatenate all segments with silence gaps
        _fps = 44100
        _gap_sec = GAP_MS / 1000.0
        _silence_arr = np.zeros((int(_fps * _gap_sec), 2), dtype=np.float32)
        _silence_clip = AudioArrayClip(_silence_arr, fps=_fps)

        current_time = 0.0
        caption_segments: List[Dict] = []
        moviepy_clips = []

        for idx, (line, char_cfg, seg_path, word_timings) in enumerate(results):
            char_name = line.get("char", "NARRATOR")
            text = line.get("text", "")

            if not os.path.exists(seg_path) or os.path.getsize(seg_path) < 100:
                logger.warning(f"Skipping missing segment: {seg_path}")
                continue

            aclip = AudioFileClip(seg_path)
            duration_sec = aclip.duration
            moviepy_clips.append(aclip)
            if idx < len(results) - 1:
                moviepy_clips.append(_silence_clip)

            if word_timings:
                for wt in word_timings:
                    wt["start"] += current_time
                    wt["end"] += current_time
                for j in range(0, len(word_timings), CAPTION_CHUNK_SIZE):
                    chunk = word_timings[j: j + CAPTION_CHUNK_SIZE]
                    caption_segments.append({
                        "char": char_name,
                        "text": " ".join(w["word"] for w in chunk),
                        "start": chunk[0]["start"],
                        "end": chunk[-1]["end"],
                        "color": char_cfg.get("caption_color", (255, 230, 0, 255)),
                        "emoji": char_cfg.get("emoji", ""),
                    })
            else:
                caption_segments.append({
                    "char": char_name,
                    "text": text,
                    "start": current_time,
                    "end": current_time + duration_sec,
                    "color": char_cfg.get("caption_color", (255, 255, 255, 255)),
                    "emoji": char_cfg.get("emoji", ""),
                })

            current_time += duration_sec + _gap_sec

        final_audio = concatenate_audioclips(moviepy_clips)
        final_audio.write_audiofile(output_path, fps=_fps, logger=None)
        total = final_audio.duration
        final_audio.close()
        for c in moviepy_clips:
            try:
                c.close()
            except Exception:
                pass

        engine = "ElevenLabs" if use_elevenlabs else "edge-tts"
        logger.info(f"Multi-char TTS ({engine}): {len(dialogue)} lines → {total:.1f}s, {len(caption_segments)} captions")
        return caption_segments

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
