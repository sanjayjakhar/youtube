import json
import logging
from typing import Dict, List
from groq import Groq
from config import GROQ_API_KEY, CHARACTERS

logger = logging.getLogger(__name__)
_MODEL = "llama-3.3-70b-versatile"

# Human-readable descriptions for each character (for the LLM prompt)
_CHAR_DESC = {
    "HULK":          "Hulk — bahut powerful, simple bolta hai, 'Hulk' naam use karta hai khud ke liye, kabhi kabhi gussa",
    "IRON_MAN":      "Iron Man (Tony Stark) — confident, smart, tech jokes karta hai, thoda arrogant",
    "SPIDER_MAN":    "Spider-Man — energetic, funny, young, relatable, jokes karta hai serious situations mein bhi",
    "THOR":          "Thor — dramatic, royal Asgardian style, 'Mjolnir' aur 'Asgard' mention karta hai",
    "BLACK_PANTHER": "Black Panther — calm, wise, regal, thoughtful responses",
    "DEADPOOL":      "Deadpool — hyper, breaks 4th wall, random jokes, completely unpredictable",
    "LOKI":          "Loki — cunning, sarcastic, always has a hidden plan, dramatic",
    "SHAKTIMAN":     "Shaktiman — Indian superhero style, values, moral lessons deta hai",
    "REPORTER":      "Indian female news reporter — professional, curious, sharp questions poochti hai",
    "REPORTER_M":    "Indian male news reporter — professional, excited, follow-up questions karta hai",
    "ANCHOR":        "Indian female TV anchor — confident, dramatic delivery, breaking news style",
    "SCIENTIST":     "Indian male scientist — excited about discovery, technical terms use karta hai",
    "SCIENTIST_F":   "Indian female scientist — brilliant, passionate, research facts bolta hai",
    "CHILD":         "Indian curious child — innocent questions, surprised easily, very enthusiastic",
    "VILLAIN":       "Villain — menacing, slow speech, dramatic threats",
    "PUBLIC":        "Indian common person — relatable, surprised, everyday language",
    "NARRATOR":      "Narrator — sets the scene, max 12 words, neutral voice",
    "CRICKETER":     "Indian cricketer — passionate about cricket, energetic, uses cricket metaphors",
    "CHEF":          "Indian chef — very proud of food, dramatic about cooking, uses food metaphors",
    "TEACHER":       "Indian teacher — authoritative, asks questions back, old-school style",
    "POLICE":        "Indian police officer — serious, by-the-book, suspicious of everything",
    "GHOST":         "Ghost — dramatic, lonely, gets confused by modern India",
    "ROBOT":         "Robot — very literal, confused by human emotions, speaks in instructions",
    "DADI":          "Indian grandma — wisdom with humor, old-school values, calls everyone beta",
    "SHARMA_JI":     "Sharma Ji neighbor — extremely nosy, compares everything to his son, Hindi colony uncle",
}


def generate_video_content(
    trending_topics: List[str],
    category: str,
    char1: str = "HULK",
    char2: str = "REPORTER",
) -> Dict:
    client = Groq(api_key=GROQ_API_KEY)
    topics_str = "\n".join(f"- {t}" for t in trending_topics[:12])

    c1_desc = _CHAR_DESC.get(char1, char1)
    c2_desc = _CHAR_DESC.get(char2, char2)
    c1_emoji = CHARACTERS.get(char1, {}).get("emoji", "")
    c2_emoji = CHARACTERS.get(char2, {}).get("emoji", "")

    prompt = f"""Tu ek viral Hindi YouTube Shorts creator hai jo Indian audience ke liye content banata hai.

Video mein AI-generated cinematic visuals honge — do characters jo SCREEN PE DIKHENGE aur KHUD bolenge:

CHARACTER 1: {char1} {c1_emoji}
  → {c1_desc}

CHARACTER 2: {char2} {c2_emoji}
  → {c2_desc}

Content Category: {category}

Trending topics (inme se koi ek choose kar ya apna topic laga jo category se match kare):
{topics_str}

IMPORTANT: {char1} aur {char2} directly ek doosre se baat karein — jaise vo screen pe saamne baithe hain.
{char1} ki dialogue {char1} ki personality ke hisaab se ho. {char2} ki dialogue {char2} ki personality se.

SIRF valid JSON return kar:

{{
  "chosen_topic": "...",
  "title": "...",
  "hook_text": "...",
  "dialogue": [
    {{"char": "NARRATOR", "text": "..."}},
    {{"char": "{char2}", "text": "..."}},
    {{"char": "{char1}", "text": "..."}},
    {{"char": "{char2}", "text": "..."}},
    {{"char": "{char1}", "text": "..."}}
  ],
  "description": "...",
  "tags": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."],
  "search_keywords": ["...", "...", "..."]
}}

STRICT RULES:
- title: emoji se shuru, 65 chars se kam, end mein " #Shorts", Hindi/Hinglish mein
  * Example: "💚 HULK KA PEHLA INTERVIEW! #Shorts" ya "🕷️ SPIDER-MAN PAKDA GAYA! #Shorts"
- hook_text: 4-6 CAPITAL words with emoji (jaise "{char1.replace('_',' ')} NE KUCH AUR HI BOLA 😱")
- dialogue: exactly 15-18 lines total
  * Line 1: NARRATOR — scene set kare in max 12 words (e.g. "Aaj {char2} ne {char1} ka interview liya")
  * Baaki lines: {char1} aur {char2} ki DIRECT baat-cheet — seedha ek doosre se
  * Har line: 8-14 words, natural spoken Hindi
  * End se 3rd line pe UNEXPECTED TWIST aaye — shocking ya funny moment
  * Last line ({char2} ya {char1} bolein): "Aisa content dekhna hai? Abhi follow kar le!"
- Each character must speak in their OWN style (upar described)
- description: 180-220 chars, Hindi summary + #shorts #viral #trending #india #hindi
- tags: 10 tags — character names + trending Indian tags
- search_keywords: 2-3 English words for scene visuals
- BILKUL NO asterisk, brackets, ya bullet points in dialogue text
"""

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.92,
        max_tokens=1600,
    )

    data = json.loads(response.choices[0].message.content)

    if "#Shorts" not in data.get("title", "") and "#shorts" not in data.get("title", ""):
        data["title"] = data["title"].rstrip() + " #Shorts"

    desc = data.get("description", "")
    for tag in ["#shorts", "#viral", "#trending", "#india", "#hindi"]:
        if tag not in desc.lower():
            desc += f" {tag}"
    data["description"] = desc.strip()[:500]

    # Ensure only valid chars appear in dialogue
    allowed = {char1, char2, "NARRATOR"}
    dialogue = [d for d in data.get("dialogue", []) if d.get("char") in allowed]
    data["dialogue"] = dialogue

    logger.info(f"Category : {category[:45]}")
    logger.info(f"Topic    : {data.get('chosen_topic')}")
    logger.info(f"Title    : {data.get('title')}")
    logger.info(f"Hook     : {data.get('hook_text')}")
    logger.info(f"Chars    : {char1} + {char2}")
    logger.info(f"Dialogue : {len(dialogue)} lines")
    return data
