# Iran Proxy Finder

A fully dockerized utility that scrapes publicly available Iranian proxies, tests them against `https://ib.tejaratbank.ir/`, and stores the responsive proxies in `working_proxies.json`.

## Project Structure
```
.
├── docker-compose.yml
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scraper.py
│   ├── tester.py
│   ├── run.py
│   └── working_proxies.json (generated after first run)
```

## Prerequisites
- Docker
- Docker Compose

## Quick Start
1. Clone the repository:
   ```bash
   git clone <your-private-repo-url>
   cd iran_proxy_finder
   ```
2. Build and run:
   ```bash
   docker compose up --build
   ```
   The service starts automatically and prints scrape/test progress to the console. On the first run, `app/working_proxies.json` is created with successful proxies.

## Re-running Manually
To re-run the workflow after updating code or clearing results, run:
```bash
docker compose up --build
```

## Output
- Working proxies (HTTP 200 responses) are saved to `app/working_proxies.json` in the format:
  ```json
  [
    {"proxy": "IP:PORT", "latency": 1.234}
  ]
  ```

## Extending
- Adjust the scrape source in `app/scraper.py` if the proxy provider changes.
- Modify the target URL or timeout in `app/tester.py` to validate proxies against different services.
- Extend `app/run.py` to add logging, scheduling, or alternative persistence as needed.
