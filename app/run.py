import json
from pathlib import Path

from scraper import get_proxies
from tester import test_proxy

OUTPUT_FILE = Path(__file__).parent / "working_proxies.json"


def main() -> None:
    print("Scraping proxies...")
    proxies = get_proxies()
    print(f"Total proxies found: {len(proxies)}")

    working = []
    for proxy in proxies:
        is_working, latency = test_proxy(proxy)
        if is_working and latency is not None:
            working.append({"proxy": proxy, "latency": round(latency, 3)})
            print(f"[OK] {proxy} - {latency:.3f}s")
        else:
            print(f"[FAIL] {proxy}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(working, f, indent=2)

    print("\nSummary:")
    print(f"Working proxies: {len(working)}")
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
