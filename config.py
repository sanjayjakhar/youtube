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
CAPTION_FONT_SIZE = 68
CAPTION_Y_POSITION = 1400

# Rotating content categories — agent cycles through all of these
CONTENT_CATEGORIES = [
    "funny aur comedy — hasane wali funny situations aur jokes",
    "prank videos — shocking reactions aur surprise moments",
    "optical illusion aur brain tricks — dimaag ko chakkar dene wali visuals",
    "loop video facts — jinhe baar baar dekhne ka dil kare (seamless loop concept)",
    "amazing facts aur gyan — shocking sach jo log nahi jaante",
    "science experiments — ghar par aasaani se karne wale experiments",
    "kids entertainment — bacchon ke liye mazedar aur creative content",
    "action aur fight stunts — thrilling aur exciting moments",
    "motivational story — zindagi badalne wali short kahani",
]
