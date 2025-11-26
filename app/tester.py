import time
from typing import Tuple

import requests

TARGET_URL = "https://ib.tejaratbank.ir/"


def test_proxy(proxy: str) -> Tuple[bool, float | None]:
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }

    try:
        start = time.monotonic()
        response = requests.get(TARGET_URL, proxies=proxies, timeout=8)
        latency = time.monotonic() - start
        if response.status_code == 200:
            return True, latency
    except requests.RequestException:
        pass
    return False, None


__all__ = ["test_proxy"]
