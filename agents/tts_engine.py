import asyncio
import os
import logging
import tempfile
import shutil
from typing import List, Dict

import numpy as np
import edge_tts
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip

from config import CHARACTERS, CAPTION_CHUNK_SIZE

logger = logging.getLogger(__name__)

GAP_MS = 320  # silence between dialogue lines


async def _generate_segment(text: str, voice: str, rate: str, output_path: str) -> List[Dict]:
    """Generate TTS for one line, return sentence-level timings."""
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

    # Distribute sentence → word timings proportionally
    word_timings: List[Dict] = []
    for sentence in sentence_timings:
        words = sentence["text"].split()
        if not words:
            continue
        dur_per_word = (sentence["end"] - sentence["start"]) / len(words)
        for i, word in enumerate(words):
            word_timings.append({
                "word": word,
                "start": sentence["start"] + i * dur_per_word,
                "end": sentence["start"] + (i + 1) * dur_per_word,
            })

    return word_timings


async def _generate_all_async(dialogue: List[Dict], temp_dir: str) -> list:
    results = []
    for i, line in enumerate(dialogue):
        char_name = line.get("char", "NARRATOR")
        text = line.get("text", "").strip()
        if not text:
            continue
        char_cfg = CHARACTERS.get(char_name, CHARACTERS["NARRATOR"])
        seg_path = os.path.join(temp_dir, f"seg_{i:03d}.mp3")
        word_timings = await _generate_segment(
            text,
            char_cfg["voice"],
            char_cfg["rate"],
            seg_path,
        )
        results.append((line, char_cfg, seg_path, word_timings))
    return results


def generate_multi_char_tts(dialogue: List[Dict], output_path: str) -> List[Dict]:
    """Generate multi-character audio + return per-char timed captions."""
    temp_dir = tempfile.mkdtemp()
    try:
        results = asyncio.run(_generate_all_async(dialogue, temp_dir))

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

            # Get duration via moviepy
            aclip = AudioFileClip(seg_path)
            duration_sec = aclip.duration
            moviepy_clips.append(aclip)
            if idx < len(results) - 1:
                moviepy_clips.append(_silence_clip)

            # Build caption chunks
            if word_timings:
                for wt in word_timings:
                    wt["start"] += current_time
                    wt["end"] += current_time
                for j in range(0, len(word_timings), CAPTION_CHUNK_SIZE):
                    chunk = word_timings[j : j + CAPTION_CHUNK_SIZE]
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

        # Concatenate and export
        final_audio = concatenate_audioclips(moviepy_clips)
        final_audio.write_audiofile(output_path, fps=_fps, logger=None)
        total = final_audio.duration
        final_audio.close()
        for c in moviepy_clips:
            try: c.close()
            except Exception: pass

        logger.info(f"Multi-char TTS: {len(dialogue)} lines → {total:.1f}s, {len(caption_segments)} captions")
        return caption_segments

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── Legacy single-voice (kept for fallback) ───────────────────────────────────

async def _stream_single(text: str, output_path: str, voice: str, rate: str) -> List[Dict]:
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
            word_timings.append({"word": w, "start": s["start"] + i * dpw, "end": s["start"] + (i + 1) * dpw})
    return word_timings


def generate_tts(text: str, output_path: str) -> List[Dict]:
    cfg = CHARACTERS["RAVI"]
    return asyncio.run(_stream_single(text, output_path, cfg["voice"], cfg["rate"]))


def group_into_captions(word_timings: List[Dict], chunk_size: int = CAPTION_CHUNK_SIZE) -> List[Dict]:
    captions = []
    for i in range(0, len(word_timings), chunk_size):
        chunk = word_timings[i : i + chunk_size]
        captions.append({
            "char": "RAVI",
            "text": " ".join(w["word"] for w in chunk),
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "color": CHARACTERS["RAVI"]["caption_color"],
            "emoji": CHARACTERS["RAVI"]["emoji"],
        })
    return captions
