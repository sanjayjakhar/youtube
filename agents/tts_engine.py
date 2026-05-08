import asyncio
import logging
from typing import List, Dict
import edge_tts
from config import TTS_VOICE, CAPTION_CHUNK_SIZE

logger = logging.getLogger(__name__)


async def _stream_tts(text: str, output_path: str) -> List[Dict]:
    communicate = edge_tts.Communicate(text, TTS_VOICE)
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

    # Distribute sentence timings into per-word timings proportionally
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

    logger.info(f"TTS complete: {len(word_timings)} words from {len(sentence_timings)} sentences, saved to {output_path}")
    return word_timings


def generate_tts(text: str, output_path: str) -> List[Dict]:
    return asyncio.run(_stream_tts(text, output_path))


def group_into_captions(word_timings: List[Dict], chunk_size: int = CAPTION_CHUNK_SIZE) -> List[Dict]:
    captions = []
    i = 0
    while i < len(word_timings):
        chunk = word_timings[i : i + chunk_size]
        captions.append(
            {
                "text": " ".join(w["word"] for w in chunk),
                "start": chunk[0]["start"],
                "end": chunk[-1]["end"],
            }
        )
        i += chunk_size
    return captions
