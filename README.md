# Iran Proxy Finder

A fully dockerized utility that scrapes publicly available Iranian proxies, tests them against `https://ib.tejaratbank.ir/`, and stores the responsive proxies in `working_proxies.json`. A lightweight Flask web UI lets you start scans and follow logs in real time.

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
2. Build and run (default web UI port is 5000). If that port is busy, set `HOST_PORT` to any free port (for example 5001):
   ```bash
   docker compose up --build
   # or
   HOST_PORT=5001 docker compose up --build
   ```
3. Open the web dashboard at [http://localhost:5000](http://localhost:5000).
   - Click **Start Scan** to fetch and validate proxies.
   - Watch progress in the live log panel.
   - Results are saved to `app/working_proxies.json`.

## Re-running Manually
- Start another scan from the web UI at any time.
- Or run the workflow once in CLI mode from the container/app folder:
  ```bash
  python run.py --once
  ```

## Output
- Working proxies (HTTP 200 responses) are saved to `app/working_proxies.json` in the format:
  ```json
  [
    {"proxy": "IP:PORT", "latency": 1.234}
  ]
  ```
- Latest logs are always visible from the dashboard (and printed to container stdout).

## Extending
- Adjust the scrape source in `app/scraper.py` if the proxy provider changes.
- Modify the target URL or timeout in `app/tester.py` to validate proxies against different services.
- Extend `app/run.py` to add scheduling, authentication for the UI, or alternative persistence as needed.

## Notes
- Database migrations are not used in this project. If you add a database later, remember to handle migrations manually.
