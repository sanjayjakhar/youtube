import os
import logging
import time
from typing import Optional
import requests

logger = logging.getLogger(__name__)

EL_BASE = "https://api.elevenlabs.io/v1"

# ElevenLabs voice IDs — chosen for character personality
_VOICE_IDS = {
    "HULK":          "pNInz6obpgDQGcFmaJgB",  # Adam — deep, powerful
    "THOR":          "VR6AewLTigWG4xSOukaG",  # Arnold — authoritative, rough
    "IRON_MAN":      "ErXwobaYiN019PkySvjV",  # Antoni — confident, smooth
    "SPIDER_MAN":    "TxGEqnHWrfWFTfGW9XjX",  # Josh — young, energetic
    "DEADPOOL":      "yoZ06aMxZJJ28mfd3POQ",  # Sam — raspy, chaotic
    "LOKI":          "VR6AewLTigWG4xSOukaG",  # Arnold — cunning baritone
    "BLACK_PANTHER": "pNInz6obpgDQGcFmaJgB",  # Adam — calm, deep
    "SHAKTIMAN":     "ErXwobaYiN019PkySvjV",  # Antoni — heroic
    "VILLAIN":       "pNInz6obpgDQGcFmaJgB",  # Adam — menacing slow
    "REPORTER":      "21m00Tcm4TlvDq8ikWAM",  # Rachel — female, professional
    "ANCHOR":        "EXAVITQu4vr4xnSDxMaL",  # Bella — female, warm
    "REPORTER_M":    "ErXwobaYiN019PkySvjV",  # Antoni — male reporter
    "SCIENTIST":     "ErXwobaYiN019PkySvjV",  # Antoni — excited
    "SCIENTIST_F":   "AZnzlk1XvdvUeBnXmlld",  # Domi — female intense
    "CHILD":         "MF3mGyEYCl7XYWbV9V6O",  # Elli — young, high pitch
    "PUBLIC":        "21m00Tcm4TlvDq8ikWAM",  # Rachel — everyday person
    "NARRATOR":      "ErXwobaYiN019PkySvjV",  # Antoni — neutral narrator
    # Real-world Indian character voices
    "CRICKETER":     "TxGEqnHWrfWFTfGW9XjX",  # Josh — energetic passionate
    "CHEF":          "VR6AewLTigWG4xSOukaG",  # Arnold — enthusiastic
    "TEACHER":       "ErXwobaYiN019PkySvjV",  # Antoni — calm authoritative
    "POLICE":        "pNInz6obpgDQGcFmaJgB",  # Adam — firm, deep
    "GHOST":         "pNInz6obpgDQGcFmaJgB",  # Adam — slow eerie
    "ROBOT":         "ErXwobaYiN019PkySvjV",  # Antoni — flat delivery
    "DADI":          "AZnzlk1XvdvUeBnXmlld",  # Domi — elderly female
    "SHARMA_JI":     "VR6AewLTigWG4xSOukaG",  # Arnold — exaggerated
}

# Voice style settings per character personality
_VOICE_SETTINGS = {
    "HULK":      {"stability": 0.8, "similarity_boost": 0.9, "style": 0.1, "use_speaker_boost": True},
    "THOR":      {"stability": 0.75, "similarity_boost": 0.85, "style": 0.2, "use_speaker_boost": True},
    "DEADPOOL":  {"stability": 0.3, "similarity_boost": 0.7, "style": 0.8, "use_speaker_boost": True},
    "SPIDER_MAN":{"stability": 0.5, "similarity_boost": 0.8, "style": 0.5, "use_speaker_boost": True},
    "CHILD":     {"stability": 0.6, "similarity_boost": 0.8, "style": 0.6, "use_speaker_boost": True},
    "default":   {"stability": 0.55, "similarity_boost": 0.75, "style": 0.3, "use_speaker_boost": True},
}


def generate_elevenlabs_audio(text: str, char_name: str, output_path: str, api_key: str) -> bool:
    """Generate audio for one dialogue line using ElevenLabs multilingual v2."""
    voice_id = _VOICE_IDS.get(char_name, _VOICE_IDS["NARRATOR"])
    settings = _VOICE_SETTINGS.get(char_name, _VOICE_SETTINGS["default"])

    for attempt in range(3):
        try:
            resp = requests.post(
                f"{EL_BASE}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": settings,
                },
                timeout=60,
            )
            if resp.status_code in (401, 402):
                logger.warning(f"ElevenLabs {resp.status_code} — quota/auth issue, skipping ElevenLabs")
                return False
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                logger.warning(f"ElevenLabs rate limited — waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            size = os.path.getsize(output_path)
            if size < 1000:
                logger.warning(f"ElevenLabs audio too small ({size}B)")
                return False
            logger.debug(f"ElevenLabs: {char_name} → {size//1024}KB")
            return True
        except Exception as e:
            logger.warning(f"ElevenLabs attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return False


def check_quota(api_key: str) -> dict:
    """Check remaining ElevenLabs character quota."""
    try:
        resp = requests.get(
            f"{EL_BASE}/user/subscription",
            headers={"xi-api-key": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            used = data.get("character_count", 0)
            limit = data.get("character_limit", 10000)
            remaining = limit - used
            logger.info(f"ElevenLabs quota: {remaining}/{limit} chars remaining")
            return {"remaining": remaining, "limit": limit, "ok": remaining > 100}
        # 401 with missing_permissions = restricted key (TTS-only) — still works for audio
        if resp.status_code == 401:
            detail = resp.json().get("detail", {})
            if isinstance(detail, dict) and "missing_permissions" in detail.get("status", ""):
                logger.info("ElevenLabs key is TTS-only (no quota read) — assuming ok")
                return {"remaining": 9999, "limit": 10000, "ok": True}
            logger.warning("ElevenLabs API key invalid (401)")
            return {"remaining": 0, "limit": 0, "ok": False}
        return {"remaining": 9999, "limit": 10000, "ok": True}
    except Exception as e:
        logger.warning(f"Could not check ElevenLabs quota: {e}")
        return {"remaining": 9999, "limit": 10000, "ok": True}
