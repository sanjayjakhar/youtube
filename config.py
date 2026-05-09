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

# Two main characters — different voices, different caption colors
CHARACTERS = {
    "RAVI": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+22%",                          # Natural male speed
        "caption_color": (255, 230, 0, 255),     # Yellow
        "name_color": (255, 180, 0, 255),
        "emoji": "👦",
    },
    "PRIYA": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+18%",                          # Natural female speed
        "caption_color": (100, 225, 255, 255),   # Cyan
        "name_color": (255, 100, 200, 255),
        "emoji": "👧",
    },
    "NARRATOR": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+12%",
        "caption_color": (255, 255, 255, 255),   # White
        "name_color": None,
        "emoji": "",
    },
}

# Rotating content categories
CONTENT_CATEGORIES = [
    "do dost ki funny conversation — ek unexpected twist ke saath jo end mein sabko surprise kare",
    "prank gone wrong — jo prank karna tha woh ulta pad gaya karne wale pe hi",
    "optical illusion reveal — ek cheez jo dikhti kuch hai, hoti kuch aur — shocking ending",
    "real life loop situation — ek aisi galti jo baar baar hoti hai, jab tak samjha tab tak der ho gayi",
    "shocking facts conversation — do log baat karte karte aisa fact batayein jo sunke aankh khuli reh jaye",
    "science experiment twist — ghar pe kuch try karo, result bilkul unexpected nikle",
    "kids vs parents funny — baccha parents ko hi ulta padhane lage, parents ke hosh ud jayein",
    "dare gone wrong — koi stunt ya dare try kiya jo bilkul ulta ho gaya",
    "motivational twist story — lagta hai haar jaayega, but last second mein aisa kuch ho jo sabko rula de",
]
