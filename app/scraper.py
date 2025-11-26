import re
from typing import List

import requests
from bs4 import BeautifulSoup

PROXY_LIST_URL = "https://spys.one/free-proxy-list/IR/"


def fetch_proxy_page(url: str = PROXY_LIST_URL) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text


def extract_proxies(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    text_content = soup.get_text(" ")
    ip_port_pattern = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|1\d{2}|[1-9]?\d)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|1\d{2}|[1-9]?\d):\d+\b"
    )

    seen = set()
    proxies: List[str] = []

    for match in ip_port_pattern.finditer(text_content):
        proxy = match.group(0)
        if proxy not in seen:
            seen.add(proxy)
            proxies.append(proxy)

    if proxies:
        return proxies

    proxy_cells = soup.find_all("td")
    for cell in proxy_cells:
        cell_text = cell.get_text(strip=True)
        match = ip_port_pattern.search(cell_text)
        if match:
            proxy = match.group(0)
            if proxy not in seen:
                seen.add(proxy)
                proxies.append(proxy)

    return proxies


def get_proxies() -> List[str]:
    try:
        html = fetch_proxy_page()
    except requests.RequestException as exc:
        print(f"Failed to fetch proxy list: {exc}")
        return []

    proxies = extract_proxies(html)
    print(f"Extracted {len(proxies)} unique proxies.")
    return proxies


__all__ = ["get_proxies"]
