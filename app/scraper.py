import re
from typing import List

import requests
from bs4 import BeautifulSoup

SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&country=IR&timeout=10000&simplified=true",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&country=IR&timeout=10000&simplified=true",
    "https://www.proxy-list.download/api/v1/get?type=http&country=IR",
    "https://www.proxy-list.download/api/v1/get?type=https&country=IR",
    "https://free-proxy-list.net/ir",
    "https://spys.one/free-proxy-list/IR/",
]


def fetch_proxy_page(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
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

    if not proxies:
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
    all_proxies: List[str] = []
    seen = set()
    for url in SOURCES:
        try:
            html = fetch_proxy_page(url)
        except requests.RequestException as exc:
            print(f"Failed to fetch from {url}: {exc}")
            continue

        if "displayproxies" in url or "/api/v1/get" in url:
            lines = [line.strip() for line in html.splitlines() if line.strip()]
            for line in lines:
                if ":" in line and line not in seen:
                    seen.add(line)
                    all_proxies.append(line)
        else:
            extracted = extract_proxies(html)
            for proxy in extracted:
                if proxy not in seen:
                    seen.add(proxy)
                    all_proxies.append(proxy)

    print(f"Extracted {len(all_proxies)} unique proxies.")
    return all_proxies


__all__ = ["get_proxies"]
