import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

DID_BASE = "https://api.d-id.com"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }


def upload_image(image_path: str, api_key: str) -> str:
    """Upload a local image to D-ID and return its hosted URL."""
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{DID_BASE}/images",
            headers={"Authorization": f"Basic {api_key}"},
            files={"image": (os.path.basename(image_path), f, "image/jpeg")},
            timeout=60,
        )
    resp.raise_for_status()
    url = resp.json().get("url", "")
    logger.info(f"D-ID image uploaded: {url[:60]}...")
    return url


def upload_audio(audio_path: str) -> str:
    """Upload audio to catbox.moe (free, 72h public URL) for D-ID to fetch."""
    with open(audio_path, "rb") as f:
        resp = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "72h"},
            files={"fileToUpload": (os.path.basename(audio_path), f, "audio/mpeg")},
            timeout=60,
        )
    if resp.status_code == 200 and resp.text.startswith("http"):
        url = resp.text.strip()
        logger.info(f"Audio hosted: {url}")
        return url
    raise RuntimeError(f"Audio upload failed: {resp.text}")


def create_talk(image_url: str, audio_url: str, api_key: str) -> str:
    """Submit a D-ID talking-face job, return talk_id."""
    resp = requests.post(
        f"{DID_BASE}/talks",
        headers=_headers(api_key),
        json={
            "source_url": image_url,
            "script": {
                "type": "audio",
                "audio_url": audio_url,
            },
            "config": {
                "fluent": True,
                "stitch": True,
                "result_format": "mp4",
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    talk_id = resp.json()["id"]
    logger.info(f"D-ID talk created: {talk_id}")
    return talk_id


def wait_for_result(talk_id: str, api_key: str, timeout_sec: int = 180) -> str:
    """Poll until D-ID talk is done, return result video URL."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.get(
            f"{DID_BASE}/talks/{talk_id}",
            headers={"Authorization": f"Basic {api_key}"},
            timeout=15,
        )
        data = resp.json()
        status = data.get("status", "")
        if status == "done":
            url = data.get("result_url", "")
            logger.info(f"D-ID done: {url[:60]}...")
            return url
        if status == "error":
            raise RuntimeError(f"D-ID error: {data.get('error', data)}")
        logger.debug(f"D-ID status: {status} — waiting...")
        time.sleep(6)
    raise TimeoutError(f"D-ID talk {talk_id} timed out after {timeout_sec}s")


def download_video(url: str, output_path: str) -> bool:
    """Download D-ID result video to local path."""
    try:
        resp = requests.get(url, timeout=90, stream=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
        size = os.path.getsize(output_path)
        logger.info(f"D-ID video downloaded: {size // 1024}KB")
        return size > 10000
    except Exception as e:
        logger.error(f"D-ID video download failed: {e}")
        return False


def generate_talking_clip(
    image_path: str,
    audio_path: str,
    output_path: str,
    api_key: str,
) -> bool:
    """
    Full pipeline: image + audio → D-ID talking face video.
    Returns True on success.
    """
    try:
        image_url = upload_image(image_path, api_key)
        audio_url = upload_audio(audio_path)
        talk_id = create_talk(image_url, audio_url, api_key)
        result_url = wait_for_result(talk_id, api_key)
        return download_video(result_url, output_path)
    except Exception as e:
        logger.error(f"D-ID talking clip failed: {e}")
        return False
