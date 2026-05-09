import os
import time
import logging
import random
import urllib.parse
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# Cinematic scene templates per category — Indian viral Shorts style
# Each entry = a full SCENE (characters + action + setting)
_SCENE_LIBRARY = {
    "science": [
        "Iron Man in a secret lab in Mumbai doing dangerous experiment, explosion of colorful chemicals, cinematic dramatic lighting, 9:16 vertical",
        "Dr Strange and Iron Man discovering shocking science fact in Indian laboratory, magical energy swirling, cinematic",
        "Hulk accidentally breaking science experiment in Indian school lab, kids shocked, funny cinematic scene",
        "two Indian scientists in futuristic lab finding unexpected result, epic reaction faces, cinematic 9:16",
        "Thor using lightning to power science experiment in India, shocked reporters watching, cinematic",
    ],
    "prank": [
        "Loki doing a prank on Thor in Indian street market, crowd laughing, cinematic 9:16 vertical",
        "Spider-Man prank gone wrong in Mumbai bazaar, shopkeeper shocked, viral shorts style cinematic",
        "Deadpool pranking Indian public on street, everyone shocked and laughing, cinematic scene",
        "funny cartoon monkey in hoodie pulling prank in Indian chai shop, shocked faces, vibrant cinematic",
        "Iron Man suit malfunction prank in India, crowd reaction, dramatic cinematic style",
    ],
    "optical illusion": [
        "Doctor Strange creating mind-bending optical illusion in India, reality bending, cinematic 9:16",
        "Wanda Maximoff warping reality in Indian city, people confused and shocked, epic cinematic",
        "surreal optical illusion scene in Indian street, people questioning reality, vibrant dramatic",
        "Strange portal revealing impossible scene to Indian crowd, jaw dropping moment, cinematic",
    ],
    "loop": [
        "Deadpool stuck in a funny time loop in India, same moment repeating, comic style cinematic",
        "Iron Man experiencing groundhog day in Indian office, confused expression, cinematic",
        "Spider-Man in repeating loop situation in Mumbai, frustrated expression, funny cinematic",
    ],
    "facts": [
        "Hulk being interviewed by Indian news reporter on live TV, breaking news studio, cinematic 9:16",
        "Thor explaining shocking facts to Indian journalist with mic, newsroom background, dramatic",
        "Iron Man press conference in India revealing shocking fact, reporters shocked, cinematic",
        "Black Panther being interviewed by Indian anchor, african king meets Indian media, cinematic",
        "Avengers giving shocking interview to Indian news channel, studio lighting, dramatic cinematic",
    ],
    "kids": [
        "Spider-Man teaching kids in Indian school, children amazed and happy, heartwarming cinematic",
        "Iron Man visiting Indian children hospital, tiny kids in awe, emotional cinematic scene",
        "Hulk gently playing with Indian kids in park, funny wholesome scene, vibrant cinematic",
        "Thor babysitting Indian kids who ask too many questions, funny cinematic 9:16",
        "Avengers heroes at Indian school, kids interviewing superheroes, vibrant joyful cinematic",
    ],
    "dare": [
        "Deadpool attempting impossible dare in India that goes completely wrong, cinematic 9:16",
        "Iron Man accepting a dare from Indian public that backfires hilariously, crowd reaction",
        "Spider-Man doing extreme dare stunt in Mumbai that fails unexpectedly, cinematic",
        "Thor accepting dare from Indian kids, unexpected result, funny dramatic cinematic",
    ],
    "motivational": [
        "Iron Man giving emotional motivational speech to Indian crowd in stadium, cinematic 9:16",
        "Black Panther inspiring Indian youth, epic speech scene, dramatic lighting cinematic",
        "Thor standing with Indian hero, both looking at sunset over Mumbai, inspiring cinematic",
        "Avengers rallying Indian public after setback, emotional powerful scene, cinematic",
        "Spider-Man saving Indian family from danger, heartwarming hero moment, cinematic",
    ],
    "funny": [
        "Hulk confused at Indian wedding traditions, awkward funny moment, cinematic 9:16",
        "Thor trying to eat spicy Indian food for first time, dramatic reaction, funny cinematic",
        "Iron Man stuck in Indian traffic jam, frustrated, relatable funny cinematic",
        "Deadpool doing Indian street food challenge, hilarious reaction, vibrant cinematic",
        "Avengers at Indian family dinner, chaos and confusion, funny cinematic scene",
    ],
}

_DEFAULT_SCENES = [
    "Hulk and Iron Man having intense argument in Indian setting, dramatic cinematic 9:16",
    "Spider-Man surprised by something shocking in India, jaw drop moment, cinematic",
    "Thor reacting to unexpected twist in Indian city, dramatic cinematic scene",
    "Iron Man interview with Indian reporter going wrong, cinematic viral shorts style",
    "Avengers discussing shocking discovery in Mumbai, dramatic lighting cinematic 9:16",
]


def _get_scene_pool(category: str) -> List[str]:
    for key, scenes in _SCENE_LIBRARY.items():
        if key in category.lower():
            return scenes
    return _DEFAULT_SCENES


def _build_prompt(base_scene: str, topic_hint: str) -> str:
    topic_part = f", topic: {topic_hint[:50]}" if topic_hint else ""
    return (
        f"{base_scene}{topic_part}, "
        f"ultra detailed, high quality render, vibrant colors, "
        f"YouTube Shorts viral style, no text overlay, no watermark, "
        f"portrait 9:16 vertical composition"
    )


def _download_image(prompt: str, output_path: str, seed: int = 42) -> bool:
    encoded = urllib.parse.quote(prompt)
    url = (
        f"{POLLINATIONS_BASE}/{encoded}"
        f"?width=1080&height=1920&nologo=true&seed={seed}"
    )
    wait_times = [30, 60, 90]  # retry backoff — gives Pollinations.ai time to reset
    for attempt, wait in enumerate(wait_times + [None], 1):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            if resp.status_code == 429:
                if wait is not None:
                    logger.info(f"Rate limited — waiting {wait}s before retry {attempt + 1}")
                    time.sleep(wait)
                    continue
                else:
                    logger.warning("Rate limited — giving up on this image")
                    return False
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            size = os.path.getsize(output_path)
            if size < 8000:
                logger.warning(f"Image suspiciously small ({size}B) — skipping")
                return False
            logger.info(f"Scene image: {os.path.basename(output_path)} ({size // 1024}KB)")
            return True
        except Exception as e:
            if wait is not None:
                logger.warning(f"Attempt {attempt} failed ({e}) — retrying in {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Image download failed after retries: {e}")
                return False
    return False


def generate_scene_images(
    category: str,
    chosen_topic: str,
    work_dir: str,
    count: int = 5,
) -> List[str]:
    """
    Generate `count` cinematic scene images for the video slideshow.
    Returns list of successfully downloaded image file paths.
    """
    pool = _get_scene_pool(category)

    # Shuffle so each video looks different
    seed_base = int(time.time()) % 99999
    random.seed(seed_base)
    selected = random.sample(pool, min(count, len(pool)))
    if len(selected) < count:
        # Pad with default scenes if pool is small
        extras = random.sample(_DEFAULT_SCENES, count - len(selected))
        selected += extras

    paths = []
    for i, base_scene in enumerate(selected):
        prompt = _build_prompt(base_scene, chosen_topic)
        out_path = os.path.join(work_dir, f"scene_{i:02d}.jpg")
        if _download_image(prompt, out_path, seed=seed_base + i):
            paths.append(out_path)
        time.sleep(3)  # rate limit gap between images

    logger.info(f"Generated {len(paths)}/{count} scene images for category: {category[:40]}")
    return paths
