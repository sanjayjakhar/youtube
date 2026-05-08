import json
import logging
from typing import Dict
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

_MODEL = "llama-3.3-70b-versatile"

_TRENDING_HINDI_TAGS = [
    "#shorts", "#viral", "#trending", "#india", "#hindi",
    "#ytshorts", "#viralvideo", "#subscribe", "#youtube",
    "#reels", "#indiatrending", "#desi",
]


def generate_video_content(trending_topics: list, category: str) -> Dict:
    client = Groq(api_key=GROQ_API_KEY)

    topics_str = "\n".join(f"- {t}" for t in trending_topics[:12])

    prompt = f"""Tu ek viral Hindi YouTube Shorts creator hai jo Indian audience ke liye content banata hai.

Content Category: {category}

Trending topics:
{topics_str}

In topics mein se BEST topic choose kar jo category ke saath match kare aur maximum views laaye.

SIRF valid JSON return kar, koi markdown nahi, koi code block nahi:

{{
  "chosen_topic": "...",
  "title": "...",
  "hook_text": "...",
  "script": "...",
  "description": "...",
  "tags": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."],
  "search_keywords": ["...", "...", "..."]
}}

RULES:
- title: Hindi/Hinglish mein emoji ke saath shuru ho, 65 chars se kam, end mein " #Shorts" zaroor ho (example: "🤯 Yeh Dekh Ke Dimag Ghoom Jaayega! #Shorts")
- hook_text: 4-6 CAPITAL HINDI WORDS jo screen ke upar 3 second dikhenge — curiosity jagaaye (example: "YAAR YEH KYA HO RAHA HAI 😱" ya "99% LOG NAHI JAANTE 🤯")
- script: 115-135 simple Hindi/Hinglish words, plain text only (NO asterisk, NO brackets, NO bullet points)
  * Pehla sentence: SHOCKING hook — ek aisa sawaal ya fact jo user ko rok de
  * Beech mein: entertaining {category} content
  * Aakhri sentence: "Aisa content aur dekhna ho toh abhi follow karo!"
- description: Hindi mein 180-220 chars, interesting summary + hashtags (#shorts #viral #trending #india #hindi #facts)
- tags: 10 tags, mix of Hindi content tags aur trending English tags, all lowercase
- search_keywords: 2-3 ENGLISH keywords for stock video search matching the visual content (example: ["optical illusion", "mind trick"] or ["funny dog", "animals reaction"])
"""

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
        max_tokens=1200,
    )

    data = json.loads(response.choices[0].message.content)

    # Ensure #Shorts in title
    if "#Shorts" not in data.get("title", "") and "#shorts" not in data.get("title", ""):
        data["title"] = data["title"].rstrip() + " #Shorts"

    # Inject trending tags into description
    desc = data.get("description", "")
    for tag in ["#shorts", "#viral", "#trending", "#india", "#hindi"]:
        if tag not in desc.lower():
            desc += f" {tag}"
    data["description"] = desc.strip()[:500]

    logger.info(f"Category : {category[:40]}")
    logger.info(f"Topic    : {data.get('chosen_topic')}")
    logger.info(f"Title    : {data.get('title')}")
    logger.info(f"Hook     : {data.get('hook_text')}")
    return data
