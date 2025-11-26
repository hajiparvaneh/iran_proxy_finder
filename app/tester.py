import os
import time
from typing import Tuple

import requests

TARGET_URL = os.environ.get("TARGET_URL", "https://ib.tejaratbank.ir/")


def test_proxy(proxy: str) -> Tuple[bool, float | None]:
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }

    try:
        start = time.monotonic()
        response = requests.get(TARGET_URL, proxies=proxies, timeout=8, verify=False)
        latency = time.monotonic() - start
        if 200 <= response.status_code < 400:
            return True, latency
    except requests.RequestException:
        # Proxy failed to connect or timed out - treat as non-working proxy
        pass
    return False, None


__all__ = ["test_proxy"]
