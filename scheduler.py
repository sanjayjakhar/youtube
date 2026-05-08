"""
Daily scheduler — 2 videos per day (9 AM and 9 PM by default).
python scheduler.py   ← keep this running
"""
import time
import logging
import schedule

from config import UPLOAD_TIMES
from main import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _job():
    logger.info("Scheduled trigger fired — pipeline shuru ho raha hai")
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"Pipeline crash: {e}", exc_info=True)


for _t in UPLOAD_TIMES:
    schedule.every().day.at(_t).do(_job)
    logger.info(f"Scheduled: daily at {_t}")

logger.info(f"Scheduler active — {len(UPLOAD_TIMES)} videos/day")
logger.info("Ctrl+C se band karo")

while True:
    schedule.run_pending()
    time.sleep(30)
