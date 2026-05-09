import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
LOGS_DIR = BASE_DIR / "logs"

for _d in [OUTPUT_DIR, ASSETS_DIR / "fonts", ASSETS_DIR / "music", LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
CONTENT_NICHE = os.getenv("CONTENT_NICHE", "Hindi entertainment")
TTS_VOICE = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural")
UPLOAD_TIMES = [t.strip() for t in os.getenv("UPLOAD_TIMES", "09:00,21:00").split(",")]

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

CAPTION_CHUNK_SIZE = 4
CAPTION_FONT_SIZE = 66
CAPTION_Y_POSITION = 1380

# ── Character voice configs ───────────────────────────────────────────────────
# Each entry: voice, rate (edge-tts speed), caption_color (RGBA), emoji
# Male   Hindi voice: hi-IN-MadhurNeural
# Female Hindi voice: hi-IN-SwaraNeural
# Rate tweak = the only way to differentiate characters with free edge-tts

CHARACTERS = {
    # ── Superheroes (male, deep/powerful = slower rate) ──
    "HULK": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-18%",                            # slow + heavy
        "caption_color": (50, 230, 50, 255),       # green
        "emoji": "💚",
    },
    "IRON_MAN": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+20%",                            # fast + confident
        "caption_color": (255, 120, 0, 255),       # orange-red
        "emoji": "🦾",
    },
    "SPIDER_MAN": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+30%",                            # quick + energetic
        "caption_color": (220, 30, 30, 255),       # red
        "emoji": "🕷️",
    },
    "THOR": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-8%",                             # authoritative
        "caption_color": (80, 130, 255, 255),      # blue
        "emoji": "⚡",
    },
    "BLACK_PANTHER": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-5%",                             # calm + regal
        "caption_color": (180, 80, 255, 255),      # purple
        "emoji": "🐾",
    },
    "DEADPOOL": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+38%",                            # hyper + fast
        "caption_color": (255, 10, 10, 255),       # bright red
        "emoji": "💀",
    },
    "LOKI": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+5%",                             # smooth + cunning
        "caption_color": (0, 180, 100, 255),       # teal-green
        "emoji": "🐍",
    },
    "SHAKTIMAN": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+10%",
        "caption_color": (255, 200, 0, 255),       # golden
        "emoji": "⭐",
    },
    # ── Reporters / interviewers (female = professional) ──
    "REPORTER": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+8%",
        "caption_color": (255, 230, 80, 255),      # yellow
        "emoji": "🎤",
    },
    "REPORTER_M": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+12%",
        "caption_color": (255, 230, 80, 255),
        "emoji": "🎙️",
    },
    "ANCHOR": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+6%",
        "caption_color": (255, 180, 50, 255),
        "emoji": "📺",
    },
    # ── Other characters ──
    "SCIENTIST": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+18%",
        "caption_color": (100, 210, 255, 255),     # light blue
        "emoji": "🔬",
    },
    "SCIENTIST_F": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+15%",
        "caption_color": (100, 210, 255, 255),
        "emoji": "👩‍🔬",
    },
    "CHILD": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+45%",                            # fast + childlike
        "caption_color": (255, 160, 220, 255),     # pink
        "emoji": "👧",
    },
    "VILLAIN": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-28%",                            # menacing slow
        "caption_color": (180, 0, 0, 255),         # dark red
        "emoji": "😈",
    },
    "PUBLIC": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+22%",
        "caption_color": (200, 200, 200, 255),     # grey
        "emoji": "👥",
    },
    # ── Real-world Indian characters ──
    "CRICKETER": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+25%",                            # passionate, energetic
        "caption_color": (0, 180, 80, 255),        # cricket green
        "emoji": "🏏",
    },
    "CHEF": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+20%",                            # enthusiastic
        "caption_color": (255, 165, 0, 255),       # saffron
        "emoji": "👨‍🍳",
    },
    "TEACHER": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+5%",                             # authoritative calm
        "caption_color": (150, 200, 255, 255),     # light blue
        "emoji": "📚",
    },
    "POLICE": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-5%",                             # serious, firm
        "caption_color": (50, 100, 200, 255),      # police blue
        "emoji": "👮",
    },
    "GHOST": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-35%",                            # eerie, slow
        "caption_color": (200, 220, 255, 255),     # pale blue
        "emoji": "👻",
    },
    "ROBOT": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+0%",                             # flat, mechanical
        "caption_color": (180, 255, 220, 255),     # mint
        "emoji": "🤖",
    },
    "DADI": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "-20%",                            # slow, elderly grandma
        "caption_color": (255, 200, 150, 255),     # warm peach
        "emoji": "👵",
    },
    "SHARMA_JI": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+15%",                            # nosy neighbor trope
        "caption_color": (220, 180, 80, 255),      # mustard
        "emoji": "🤦",
    },
    # ── Narrator (no label shown) ──
    "NARRATOR": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+12%",
        "caption_color": (255, 255, 255, 255),     # white
        "emoji": "",
    },
}

# Rotating content categories
CONTENT_CATEGORIES = [
    "funny",
    "prank",
    "science",
    "kids",
    "optical illusion",
    "dare",
    "motivational",
    "ghost",
    "dadi",
    "sharma ji",
    "robot",
    "cricket",
    "teacher",
    "police",
    "facts",
]
