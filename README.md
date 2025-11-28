# Iran Proxy Finder

Find which public Iranian proxies work for your connection right now. Run locally, test quickly, and then use a working proxy with your browser’s proxy extension or system proxy settings to obtain an IR IP for opening Iran‑only websites (e.g., banks).

![Screenshot](app/assets/img/Screenshot_1_0_0.png)

## Prerequisites
- Docker and Docker Compose (recommended), or
- Python 3.11+ with `pip` (for local runs)

## Quick Start (Docker)
1. Clone the repository:
   ```bash
   git clone https://github.com/hajiparvaneh/iran_proxy_finder.git
   cd iran_proxy_finder
   ```
2. (Optional) Copy `.env.example` to `.env` and adjust values:
   ```bash
   cp .env.example .env
   # edit .env and set numbers like MAX_PROXIES, MAX_PER_TARGET
   ```
   If you skip this, default values are used automatically.
3. Build and run (default web UI port is `5000`). If that port is busy, set `HOST_PORT` to any free port (for example `5001`):
   ```bash
   docker compose up --build
   # or
   HOST_PORT=5001 docker compose up --build
   ```
4. Open the web dashboard at `http://localhost:5000` (or your `HOST_PORT`).
   - Click **Start Scan** to fetch and validate proxies.
   - Watch progress in the live log panel.
   - Results are saved to `app/working_proxies.json` by default (see `OUTPUT_FILE`).

### Environment variables
- `TARGET_URLS` – comma‑separated list of targets to test.
- `TARGET_URL` – single target to test. Defaults to general endpoints if not set.
- `MAX_PROXIES` – cap how many scraped proxies to test.
- `MAX_PER_TARGET` – limit how many proxies are tested per target.
- `VERIFY_IR` – set to `1` to keep only proxies whose exit IP geolocates to Iran.
- `OUTPUT_FILE` – output path for the results JSON (absolute or relative to `app/`).

Example:
```bash
HOST_PORT=5001 \
TARGET_URLS="https://api.ipify.org?format=json,https://httpbin.org/get" \
MAX_PROXIES=200 MAX_PER_TARGET=100 \
docker compose up --build
```

## Local Run (without Docker)
1. Create a virtual environment and install deps:
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r app/requirements.txt
   ```
2. Run once in CLI mode:
   ```bash
   TARGET_URL=https://api.ipify.org?format=json MAX_PROXIES=100 MAX_PER_TARGET=50 python app/run.py --once
   ```
3. Or start the web UI (auto-runs a scan unless `--no-autostart`):
   ```bash
   python app/run.py --host 0.0.0.0 --port 5000
   ```

## Runtime Config (Web)
- The web UI lets you set targets and limits at runtime: `targets`, `max_proxies`, and `max_per_target` can be provided when starting a scan. No redeploy or restart is needed.
- Use **Start Scan** to apply your settings, watch logs, and copy IP/Port from successful results.

## Output
- Working proxies are saved to `app/working_proxies.json` (or `OUTPUT_FILE`) in the format:
  ```json
  [
    {"proxy": "IP:PORT", "latency": 1.234, "scheme": "http", "target": "https://..."}
  ]
  ```
- Logs show success status and the connection scheme, e.g.:
  ```
  [OK] 91.107.190.207:8888 via http - 0.471s
  [FAIL] 31.25.92.114:8080
  ```
- Latest logs are visible in the web UI and printed to stdout.

## Frontend (Angular)
- A new Angular 18 dashboard lives in `frontend/`.
- Build the UI to generate production assets into `app/static/ui`:
  ```bash
  cd frontend
  npm install
  npm run build
  ```
- The Flask app automatically serves the Angular build when `app/static/ui/index.html` exists. Without a build, it falls back to the legacy Jinja template in `app/templates/legacy_index.html`.

## Web API
- `POST /start` – start a scan (no body)
- `GET /logs` – recent log lines
- `GET /status` – runner state (running, last started/finished)
- `GET /results` – JSON of working proxies

You can also provide runtime settings via `POST /start` body:
```json
{
  "targets": ["https://api.ipify.org?format=json", "https://httpbin.org/get"],
  "max_proxies": 150,
  "max_per_target": 75
}
```

## Configuration & Extending
- Scrape sources are defined in `app/scraper.py` and include multiple providers and raw lists.
- The tester in `app/tester.py` tries both `http` and `https` proxy schemes and treats `2xx–3xx` as success.
- Set `VERIFY_IR=1` to keep only proxies whose exit IP geolocates to Iran.
- Adjust targets and limits to quickly identify working proxies for your network.

## Notes
- Strict targets (e.g., banking sites) often block non‑residential or non‑IR exit IPs. First populate a proxy pool using general endpoints like `https://api.ipify.org?format=json`, then retest against the strict target.
- Public proxies are unstable and rotate often; repeat scans and higher `MAX_PROXIES` increase yield.
- Known: `MAX_PER_TARGET` may fail or be ignored if misconfigured. Ensure you pass a positive integer; if issues persist, start via the web UI and set `max_per_target` there.
- This tool does not require any secrets.

## Free & Contributing
- Free to use.
- Have an idea, found a bug, or want to contribute? Feel free to open an issue or a pull request.
