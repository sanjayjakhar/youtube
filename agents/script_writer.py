import json
import logging
from typing import Dict
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)
_MODEL = "llama-3.3-70b-versatile"


def generate_video_content(trending_topics: list, category: str) -> Dict:
    client = Groq(api_key=GROQ_API_KEY)
    topics_str = "\n".join(f"- {t}" for t in trending_topics[:12])

    # Category → character theme hint for the script
    _CHAR_THEMES = {
        "science": "Ek scientist ya superhero (Iron Man jaisa) kisi experiment ke baare mein baat kar raha ho",
        "prank": "Koi prank ya stunt kar raha ho jo ulta pad jaye, Spiderman ya Loki style",
        "facts": "Koi famous character ya superhero India mein interview de raha ho, shocking fact bataye",
        "kids": "Superhero ya famous character bacchon se milta hai, dono ki baat hoti hai",
        "dare": "Koi famous character ek dare karta hai jo fail ho jaata hai unexpectedly",
        "motivational": "Superhero ya famous character kisi ko inspire karta hai, emotional ending",
        "funny": "Famous character Indian culture mein confuse ho jaata hai, funny situation",
        "loop": "Koi character ek situation mein baar baar phans jaata hai",
        "optical illusion": "Reality mein kuch unexpected change ho jaata hai, characters shocked hain",
    }
    theme_hint = ""
    for key, hint in _CHAR_THEMES.items():
        if key in category.lower():
            theme_hint = f"\nVISUAL THEME: {hint}"
            break

    prompt = f"""Tu ek viral Hindi YouTube Shorts creator hai jo Indian audience ke liye content banata hai.
Video mein AI-generated cinematic visuals honge — jaise Iron Man, Hulk, Spider-Man, ya koi superhero Indian setting mein.

Content Category: {category}{theme_hint}

Trending topics (inme se koi ek choose kar ya apna topic laga jo category se match kare):
{topics_str}

DO CHARACTERS ke beech REAL conversation likho — RAVI (ladka) aur PRIYA (ladki).
Yeh dono famous superhero ya fictional characters ke baare mein baat karte hain,
ya khud koi superhero se connected hain, ya unhe koi ajeeb situation mein dekh rahe hain.

SIRF valid JSON return kar:

{{
  "chosen_topic": "...",
  "title": "...",
  "hook_text": "...",
  "char1": "RAVI",
  "char2": "PRIYA",
  "dialogue": [
    {{"char": "NARRATOR", "text": "..."}},
    {{"char": "RAVI", "text": "..."}},
    {{"char": "PRIYA", "text": "..."}},
    {{"char": "RAVI", "text": "..."}},
    {{"char": "PRIYA", "text": "..."}}
  ],
  "description": "...",
  "tags": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."],
  "search_keywords": ["...", "...", "..."]
}}

STRICT RULES:
- title: emoji se shuru, 65 chars se kam, end mein " #Shorts", Hindi/Hinglish mein
- hook_text: 4-6 CAPITAL words jo curiosity jagaayein (jaise "HULK KA INTERVIEW 😱" ya "IRON MAN NE KIYA KUCH AISA")
- dialogue: exactly 15-18 lines total, NARRATOR se start karo
  * NARRATOR: ek baar context set kare (max 12 words), superhero/character ka mention karo
  * Phir RAVI aur PRIYA ki natural Hindi baat-cheet — superhero/character ke baare mein
  * Har line: 8-14 words, jaise real log baat karte hain
  * End se 3rd line pe UNEXPECTED TWIST aaye — shocking ya funny
  * Last line: "Aisa content dekhna hai? Abhi follow kar le!"
- description: 180-220 chars, Hindi summary + #shorts #viral #trending #india #hindi
- tags: 10 tags — include superhero/character names + trending Indian tags
- search_keywords: 2-3 English words describing the visual scene (e.g. "hulk india interview", "iron man lab")
- BILKUL NO asterisk, brackets, ya bullet points in dialogue text
"""

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.92,
        max_tokens=1500,
    )

    data = json.loads(response.choices[0].message.content)

    if "#Shorts" not in data.get("title", "") and "#shorts" not in data.get("title", ""):
        data["title"] = data["title"].rstrip() + " #Shorts"

    desc = data.get("description", "")
    for tag in ["#shorts", "#viral", "#trending", "#india", "#hindi"]:
        if tag not in desc.lower():
            desc += f" {tag}"
    data["description"] = desc.strip()[:500]

    dialogue = data.get("dialogue", [])
    logger.info(f"Category : {category[:45]}")
    logger.info(f"Topic    : {data.get('chosen_topic')}")
    logger.info(f"Title    : {data.get('title')}")
    logger.info(f"Hook     : {data.get('hook_text')}")
    logger.info(f"Dialogue : {len(dialogue)} lines")
    return data
