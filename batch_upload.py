"""
Saare 9 categories pe abhi ek saath videos upload karo.
python batch_upload.py
"""
import time
import logging
from config import CONTENT_CATEGORIES
from main import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DELAY_BETWEEN_VIDEOS = 45  # seconds

results = []

logger.info("=" * 60)
logger.info(f"BATCH UPLOAD — {len(CONTENT_CATEGORIES)} categories")
logger.info("=" * 60)

for i, category in enumerate(CONTENT_CATEGORIES):
    logger.info(f"\n[{i+1}/{len(CONTENT_CATEGORIES)}] Category: {category[:55]}")

    try:
        success = run_pipeline(category=category)
        results.append({"category": category[:40], "success": success})
    except Exception as e:
        logger.error(f"Pipeline crashed for this category: {e}")
        results.append({"category": category[:40], "success": False, "error": str(e)})
        # YouTube quota exceeded — stop batch
        if "quotaExceeded" in str(e) or "quota" in str(e).lower():
            logger.error("YouTube quota khatam ho gaya! Kal dobara chalao.")
            break

    if i < len(CONTENT_CATEGORIES) - 1:
        logger.info(f"Next video {DELAY_BETWEEN_VIDEOS}s mein...")
        time.sleep(DELAY_BETWEEN_VIDEOS)

# Final summary
logger.info("\n" + "=" * 60)
logger.info("BATCH COMPLETE — Summary:")
for r in results:
    status = "✓ OK  " if r["success"] else "✗ FAIL"
    logger.info(f"  {status} | {r['category']}")
ok = sum(1 for r in results if r["success"])
logger.info(f"\n{ok}/{len(results)} videos successfully uploaded")
logger.info("=" * 60)
