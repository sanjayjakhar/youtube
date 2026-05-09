import os
import time
import logging
import random
import urllib.parse
from typing import List, Dict, Tuple

import requests

logger = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# Each scene entry: (image_prompt, [char1, char2])
# char names must exist in config.CHARACTERS
_SCENE_LIBRARY = {
    "facts": [
        (
            "Hulk sitting in Indian news studio being interviewed by female reporter with microphone, "
            "breaking news banner, dramatic studio lighting, both characters visible, cinematic 9:16",
            ["HULK", "REPORTER"],
        ),
        (
            "Iron Man in suit at India press conference, journalist with mic asking questions, "
            "Indian reporters crowd, cinematic dramatic lighting, 9:16 vertical",
            ["IRON_MAN", "REPORTER"],
        ),
        (
            "Thor with hammer sitting across Indian news anchor in TV studio, "
            "both clearly visible, professional news set, cinematic 9:16",
            ["THOR", "ANCHOR"],
        ),
        (
            "Black Panther in Indian news interview, female anchor with mic, "
            "Mumbai skyline visible through studio window, cinematic 9:16",
            ["BLACK_PANTHER", "REPORTER"],
        ),
        (
            "Spider-Man perched on chair in Indian TV studio, excited anchor interviewing him, "
            "live cameras visible, cinematic 9:16 vertical",
            ["SPIDER_MAN", "ANCHOR"],
        ),
    ],
    "science": [
        (
            "Iron Man and Indian female scientist in futuristic Mumbai lab, "
            "colorful chemical explosion between them, both reacting shocked, cinematic 9:16",
            ["IRON_MAN", "SCIENTIST_F"],
        ),
        (
            "Hulk accidentally smashing science lab equipment, Indian scientist watching in horror, "
            "colorful chemical reactions, dramatic cinematic 9:16",
            ["HULK", "SCIENTIST"],
        ),
        (
            "Spider-Man and Indian scientist discovering glowing experiment result, "
            "both amazed, futuristic lab background, cinematic 9:16",
            ["SPIDER_MAN", "SCIENTIST_F"],
        ),
        (
            "Thor using lightning to power giant science machine, Indian scientist taking notes, "
            "epic energy effects, cinematic 9:16",
            ["THOR", "SCIENTIST"],
        ),
    ],
    "prank": [
        (
            "Loki pulling a prank on Thor in busy Indian street market, Thor looks shocked and confused, "
            "Indian crowd laughing in background, vibrant cinematic 9:16",
            ["LOKI", "THOR"],
        ),
        (
            "Deadpool pranking Spider-Man in Mumbai, Spider-Man completely surprised, "
            "both visible face to face, funny vibrant scene, cinematic 9:16",
            ["DEADPOOL", "SPIDER_MAN"],
        ),
        (
            "Iron Man suit malfunction prank by Deadpool, Iron Man embarrassed, "
            "Indian public watching and laughing, cinematic 9:16",
            ["DEADPOOL", "IRON_MAN"],
        ),
        (
            "Loki disguised as Indian shopkeeper pranks an unsuspecting Thor, "
            "funny reveal scene, Indian bazaar background, cinematic 9:16",
            ["LOKI", "THOR"],
        ),
    ],
    "loop": [
        (
            "Spider-Man and Deadpool stuck in the same funny situation repeating, "
            "time loop visual effect, confused expressions, Indian city background, cinematic 9:16",
            ["SPIDER_MAN", "DEADPOOL"],
        ),
        (
            "Iron Man experiencing time loop in Indian traffic jam, same moment repeating, "
            "funny frustrated expression, cinematic comic style 9:16",
            ["IRON_MAN", "REPORTER"],
        ),
        (
            "Loki and Thor in repeating loop in Indian office, confused and frustrated, "
            "same desk visible multiple times, cinematic 9:16",
            ["LOKI", "THOR"],
        ),
    ],
    "optical illusion": [
        (
            "Doctor Strange creating mind-bending optical illusion in Indian city, "
            "Iron Man watching in disbelief, reality bending swirling colors, cinematic 9:16",
            ["LOKI", "IRON_MAN"],
        ),
        (
            "Loki using magic to create impossible optical illusion, Thor questioning reality, "
            "surreal colorful Indian street background, cinematic 9:16",
            ["LOKI", "THOR"],
        ),
    ],
    "kids": [
        (
            "Spider-Man sitting with Indian school children in classroom, kids amazed and raising hands, "
            "colorful classroom setting, heartwarming cinematic 9:16",
            ["SPIDER_MAN", "CHILD"],
        ),
        (
            "Hulk gently sitting with tiny Indian child who is interviewing him with toy mic, "
            "funny wholesome scene, park background, cinematic 9:16",
            ["HULK", "CHILD"],
        ),
        (
            "Thor kneeling to talk with Indian child who is asking big questions, "
            "child pointing at Mjolnir, funny wholesome, cinematic 9:16",
            ["THOR", "CHILD"],
        ),
        (
            "Iron Man explaining technology to group of Indian school children, "
            "kids in awe touching the suit, school background, cinematic 9:16",
            ["IRON_MAN", "CHILD"],
        ),
    ],
    "dare": [
        (
            "Deadpool attempting impossible dare stunt in India that goes completely wrong, "
            "Spider-Man watching and facepalming, Indian crowd, cinematic 9:16",
            ["DEADPOOL", "SPIDER_MAN"],
        ),
        (
            "Thor accepting dare from Deadpool that backfires hilariously, "
            "both looking at the result in shock, Indian setting, cinematic 9:16",
            ["THOR", "DEADPOOL"],
        ),
        (
            "Iron Man accepting impossible dare from Deadpool, "
            "dramatic fail result, Indian public reacting, cinematic 9:16",
            ["DEADPOOL", "IRON_MAN"],
        ),
    ],
    "motivational": [
        (
            "Black Panther giving powerful speech to Indian crowd in stadium, "
            "Iron Man standing beside him, epic golden hour lighting, cinematic 9:16",
            ["BLACK_PANTHER", "IRON_MAN"],
        ),
        (
            "Thor encouraging defeated Indian hero to get up, emotional powerful scene, "
            "storm clouds parting with light, cinematic 9:16",
            ["THOR", "REPORTER"],
        ),
        (
            "Spider-Man saving Indian family from danger, family looking up at him gratefully, "
            "emotional heartwarming scene, cinematic 9:16",
            ["SPIDER_MAN", "PUBLIC"],
        ),
        (
            "Iron Man giving final motivational speech before mission, "
            "Indian soldiers listening, epic dramatic lighting, cinematic 9:16",
            ["IRON_MAN", "PUBLIC"],
        ),
    ],
    "funny": [
        (
            "Hulk confused and embarrassed at Indian wedding, trying to fit in small chair, "
            "wedding guests shocked, colorful shaadi background, cinematic 9:16",
            ["HULK", "REPORTER"],
        ),
        (
            "Thor eating extremely spicy Indian food for first time, dramatic suffering reaction, "
            "Indian chef watching proudly, vibrant dhaba background, cinematic 9:16",
            ["THOR", "PUBLIC"],
        ),
        (
            "Deadpool stuck in Indian bureaucracy office, hilarious frustrated argument "
            "with babu clerk, funny dramatic scene, cinematic 9:16",
            ["DEADPOOL", "PUBLIC"],
        ),
        (
            "Iron Man at Indian family dinner table completely confused by the chaos, "
            "Indian family arguing around him, funny cinematic 9:16",
            ["IRON_MAN", "REPORTER"],
        ),
    ],
    "cricket": [
        (
            "Indian cricketer celebrating massive six at packed stadium, "
            "commentator screaming in excitement, crowd going wild, cinematic 9:16",
            ["CRICKETER", "REPORTER"],
        ),
        (
            "Indian cricketer and reporter doing dramatic post-match interview, "
            "stadium lights behind them, emotional intense moment, cinematic 9:16",
            ["CRICKETER", "ANCHOR"],
        ),
        (
            "Indian police officer stopping Indian cricketer for speeding in luxury car, "
            "cricketer trying to explain, funny confrontation, cinematic 9:16",
            ["CRICKETER", "POLICE"],
        ),
    ],
    "ghost": [
        (
            "Terrified Indian person encountering friendly ghost in old haveli, "
            "ghost trying to have a conversation, dramatic candlelit scene, cinematic 9:16",
            ["GHOST", "PUBLIC"],
        ),
        (
            "Ghost sitting with Indian grandma having chai in dark haunted house, "
            "grandma completely unbothered, ghost shocked, funny horror scene, cinematic 9:16",
            ["GHOST", "DADI"],
        ),
        (
            "Ghost appearing in Indian police station, officer trying to file complaint about ghost, "
            "hilarious bureaucracy meets supernatural, cinematic 9:16",
            ["GHOST", "POLICE"],
        ),
    ],
    "dadi": [
        (
            "Indian grandma expertly using smartphone better than tech-savvy grandson, "
            "grandson shocked, cozy home setting, funny cinematic 9:16",
            ["DADI", "CHILD"],
        ),
        (
            "Indian grandma teaching robot how to make roti, robot failing hilariously, "
            "warm kitchen setting, funny wholesome cinematic 9:16",
            ["DADI", "ROBOT"],
        ),
        (
            "Indian grandma arguing with Sharma Ji neighbor over garden fence, "
            "both being dramatic, classic Indian neighborhood, cinematic 9:16",
            ["DADI", "SHARMA_JI"],
        ),
    ],
    "sharma ji": [
        (
            "Sharma Ji gossiping with neighbor aunty about everyone on the street, "
            "nosy over-the-fence conversation, Indian colony setting, cinematic 9:16",
            ["SHARMA_JI", "PUBLIC"],
        ),
        (
            "Sharma Ji proudly comparing his son's achievements to everyone, "
            "neighbour trying to escape conversation, funny Indian neighborhood, cinematic 9:16",
            ["SHARMA_JI", "PUBLIC"],
        ),
    ],
    "robot": [
        (
            "Indian family teaching confused robot to eat with hands and speak Hindi, "
            "robot malfunctioning hilariously, colorful living room, cinematic 9:16",
            ["ROBOT", "PUBLIC"],
        ),
        (
            "Robot applying for government job at Indian government office, "
            "confused babu officer questioning it, funny bureaucracy scene, cinematic 9:16",
            ["ROBOT", "POLICE"],
        ),
    ],
    "teacher": [
        (
            "Indian teacher caught off guard when student asks unexpectedly brilliant question, "
            "classroom full of students watching, dramatic moment, cinematic 9:16",
            ["TEACHER", "CHILD"],
        ),
        (
            "Indian teacher discovering student using AI to write homework, "
            "epic confrontation at classroom blackboard, cinematic 9:16",
            ["TEACHER", "CHILD"],
        ),
    ],
    "police": [
        (
            "Indian police officer trying to arrest Loki who keeps shapeshifting, "
            "frustrated officer filing paperwork, cinematic action 9:16",
            ["POLICE", "LOKI"],
        ),
        (
            "Indian police officer stopping Deadpool who is just casually breaking all the rules, "
            "hilarious argument, city background, cinematic 9:16",
            ["POLICE", "DEADPOOL"],
        ),
        (
            "Indian police officer and Sharma Ji having dramatic confrontation in colony, "
            "neighbors watching, very Indian drama, cinematic 9:16",
            ["POLICE", "SHARMA_JI"],
        ),
    ],
}

_DEFAULT_SCENES = [
    (
        "Hulk and Iron Man having intense face-to-face argument in Indian city street, "
        "both looking at each other dramatically, cinematic 9:16",
        ["HULK", "IRON_MAN"],
    ),
    (
        "Spider-Man being interviewed by Indian reporter after saving Mumbai, "
        "both visible clearly, cinematic 9:16",
        ["SPIDER_MAN", "REPORTER"],
    ),
    (
        "Thor and Deadpool in argument in Indian market, funny dramatic confrontation, "
        "cinematic 9:16",
        ["THOR", "DEADPOOL"],
    ),
    (
        "Indian grandma and robot having chai together in traditional kitchen, "
        "funny confused robot, warm cinematic 9:16",
        ["DADI", "ROBOT"],
    ),
    (
        "Ghost and Indian police officer in dramatic staredown at police station, "
        "ghost files complaint, funny cinematic 9:16",
        ["GHOST", "POLICE"],
    ),
    (
        "Sharma Ji neighbor lecturing Indian cricketer about lifestyle, "
        "cricketer trying to escape politely, colony gate, cinematic 9:16",
        ["SHARMA_JI", "CRICKETER"],
    ),
]


def _get_scene_pool(category: str) -> List[Tuple]:
    for key, scenes in _SCENE_LIBRARY.items():
        if key in category.lower():
            return scenes
    return _DEFAULT_SCENES


def _download_image(prompt: str, output_path: str, seed: int = 42) -> bool:
    full_prompt = (
        f"{prompt}, ultra detailed, high quality render, vibrant colors, "
        f"YouTube Shorts viral style, no text overlay, no watermark, "
        f"portrait 9:16 vertical composition"
    )
    encoded = urllib.parse.quote(full_prompt)
    url = f"{POLLINATIONS_BASE}/{encoded}?width=1080&height=1920&nologo=true&seed={seed}"

    wait_times = [30, 60, 90]
    for attempt, wait in enumerate(wait_times + [None], 1):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            if resp.status_code == 429:
                if wait is not None:
                    logger.info(f"Rate limited — waiting {wait}s before retry {attempt + 1}")
                    time.sleep(wait)
                    continue
                logger.warning("Rate limited — giving up on this image")
                return False
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            size = os.path.getsize(output_path)
            if size < 8000:
                logger.warning(f"Image too small ({size}B) — skipping")
                return False
            logger.info(f"Scene image: {os.path.basename(output_path)} ({size // 1024}KB)")
            return True
        except Exception as e:
            if wait is not None:
                logger.warning(f"Attempt {attempt} failed ({e}) — retrying in {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Image download failed: {e}")
                return False
    return False


# ── Per-character portrait prompts for D-ID lip sync ─────────────────────────
_CHAR_PORTRAIT = {
    "HULK":          "Hulk green face extreme close-up, powerful angry expression, dramatic studio lighting, no background clutter, cinematic portrait 9:16",
    "IRON_MAN":      "Iron Man helmet close-up, glowing eyes, red gold suit, dramatic lighting, cinematic portrait 9:16",
    "SPIDER_MAN":    "Spider-Man mask close-up, expressive pose, dramatic red blue suit, cinematic portrait 9:16",
    "THOR":          "Thor face close-up, long blond hair, powerful expression, lightning in background, cinematic portrait 9:16",
    "BLACK_PANTHER": "Black Panther mask close-up, vibranium suit, regal expression, purple glow, cinematic portrait 9:16",
    "DEADPOOL":      "Deadpool red mask close-up, tilted head funny pose, chaotic energy, cinematic portrait 9:16",
    "LOKI":          "Loki face close-up, horned helmet, cunning smirk, green gold outfit, cinematic portrait 9:16",
    "SHAKTIMAN":     "Shaktiman Indian superhero face close-up, gold suit, heroic expression, cinematic portrait 9:16",
    "REPORTER":      "Indian female news reporter close-up portrait, professional blazer, holding microphone, studio lighting, cinematic 9:16",
    "REPORTER_M":    "Indian male news reporter close-up portrait, professional suit, holding microphone, studio lighting, cinematic 9:16",
    "ANCHOR":        "Indian female TV anchor close-up portrait, professional makeup, confident expression, studio backdrop, cinematic 9:16",
    "SCIENTIST":     "Indian male scientist close-up portrait, white lab coat, excited expression, lab background, cinematic 9:16",
    "SCIENTIST_F":   "Indian female scientist close-up portrait, white lab coat, brilliant expression, lab background, cinematic 9:16",
    "CHILD":         "Indian school child close-up portrait, school uniform, curious smile, bright eyes, cinematic 9:16",
    "VILLAIN":       "Menacing villain face close-up, dark dramatic lighting, evil expression, cinematic portrait 9:16",
    "PUBLIC":        "Ordinary Indian person face close-up, surprised expression, street background, cinematic portrait 9:16",
    "CRICKETER":     "Indian cricketer face close-up, cricket jersey, passionate expression, stadium lights, cinematic portrait 9:16",
    "CHEF":          "Indian chef face close-up portrait, white chef hat, proud expression, kitchen background, cinematic 9:16",
    "TEACHER":       "Indian male teacher face close-up portrait, formal shirt, glasses, kind authoritative expression, blackboard background, cinematic 9:16",
    "POLICE":        "Indian police officer face close-up portrait, uniform and cap, serious expression, cinematic 9:16",
    "GHOST":         "Dramatic ghost face close-up, ethereal glowing pale face, dramatic dark background, cinematic portrait 9:16",
    "ROBOT":         "Friendly robot face close-up, glowing eyes, metallic surface, cinematic portrait 9:16",
    "DADI":          "Indian elderly grandmother face close-up portrait, traditional saree, wise kind expression, warm home background, cinematic 9:16",
    "SHARMA_JI":     "Middle-aged Indian neighborhood uncle face close-up, nosy amused expression, colony background, cinematic portrait 9:16",
    "NARRATOR":      "Professional Indian narrator face close-up, neutral expression, studio lighting, cinematic portrait 9:16",
}


def generate_character_portrait(char_name: str, work_dir: str, seed: int = 12345) -> str:
    """Generate a single close-up portrait image of one character for D-ID lip sync.
    Returns the image path on success, empty string on failure."""
    prompt = _CHAR_PORTRAIT.get(char_name, f"{char_name} face close-up portrait, dramatic lighting, cinematic 9:16")
    out_path = os.path.join(work_dir, f"portrait_{char_name}.jpg")
    if _download_image(prompt, out_path, seed=seed):
        logger.info(f"Portrait generated: {char_name} → {out_path}")
        return out_path
    logger.warning(f"Portrait generation failed for {char_name}")
    return ""


def generate_scene_images(
    category: str,
    chosen_topic: str,
    work_dir: str,
    count: int = 5,
) -> Dict:
    """
    Generate cinematic scene images for the video.
    Returns: {"paths": [...], "char1": "HULK", "char2": "REPORTER"}
    All images use the SAME character pair for consistency.
    """
    pool = _get_scene_pool(category)

    seed_base = int(time.time()) % 99999
    random.seed(seed_base)

    # Pick one scene entry to fix the character pair for this video
    primary = random.choice(pool)
    primary_prompt, chars = primary

    # Find all scenes with same character pair, pad with variations if needed
    same_char_scenes = [s for s in pool if set(s[1]) == set(chars)]
    if len(same_char_scenes) < count:
        same_char_scenes = pool  # fallback: use all

    selected_prompts = random.sample(
        same_char_scenes, min(count, len(same_char_scenes))
    )
    # Pad to count if needed
    while len(selected_prompts) < count:
        selected_prompts.append(random.choice(same_char_scenes))

    paths = []
    for i, (scene_prompt, _) in enumerate(selected_prompts):
        topic_hint = f", about: {chosen_topic[:50]}" if chosen_topic else ""
        full = scene_prompt + topic_hint
        out_path = os.path.join(work_dir, f"scene_{i:02d}.jpg")
        if _download_image(full, out_path, seed=seed_base + i):
            paths.append(out_path)
        time.sleep(3)

    char1 = chars[0] if len(chars) > 0 else "HULK"
    char2 = chars[1] if len(chars) > 1 else "REPORTER"

    logger.info(
        f"Scenes: {len(paths)}/{count} images | Characters: {char1} + {char2}"
    )
    return {"paths": paths, "char1": char1, "char2": char2}
