"""Optional 2Captcha integration for reCAPTCHA v2. Set CAPTCHA_API_KEY in .env."""
import time
from typing import Optional

import requests

from src.config import CAPTCHA_API_KEY

API_BASE = "https://api.2captcha.com"


def solve_recaptcha_v2(site_key: str, page_url: str, api_key: Optional[str] = None) -> Optional[str]:
    """
    Solve reCAPTCHA v2 via 2Captcha. Returns the response token or None.
    Uses createTask/getTaskResult (poll every 5s, max 2 min).
    """
    key = (api_key or CAPTCHA_API_KEY or "").strip()
    if not key:
        return None
    try:
        r = requests.post(
            f"{API_BASE}/createTask",
            json={
                "clientKey": key,
                "task": {
                    "type": "RecaptchaV2TaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key,
                },
            },
            timeout=30,
        )
        data = r.json()
        if data.get("errorId") or not data.get("taskId"):
            return None
        task_id = data["taskId"]
        for _ in range(24):
            time.sleep(5)
            r2 = requests.post(
                f"{API_BASE}/getTaskResult",
                json={"clientKey": key, "taskId": task_id},
                timeout=30,
            )
            res = r2.json()
            if res.get("status") == "ready" and res.get("solution", {}).get("gRecaptchaResponse"):
                return res["solution"]["gRecaptchaResponse"]
            if res.get("errorId"):
                return None
        return None
    except Exception:
        return None
