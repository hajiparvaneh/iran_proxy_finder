import argparse
import json
import os
import threading
import time
from pathlib import Path
from typing import Callable, List

from flask import Flask, jsonify, render_template_string

from scraper import get_proxies
from tester import test_proxy


# The output file path is resolved relative to the script location by default,
# placing 'working_proxies.json' inside the 'app/' directory. You can override
# this by setting the OUTPUT_FILE environment variable to an absolute or relative path.
def resolve_output_path() -> Path:
    output_env = os.environ.get("OUTPUT_FILE")
    if output_env:
        env_path = Path(output_env)
        return env_path if env_path.is_absolute() else Path(__file__).parent / env_path
    return Path(__file__).parent / "working_proxies.json"


OUTPUT_FILE = resolve_output_path()

LogHandler = Callable[[str], None]


class LogBuffer:
    def __init__(self, max_entries: int = 500):
        self._entries: List[str] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def add(self, entry: str) -> None:
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]

    def snapshot(self) -> List[str]:
        with self._lock:
            return list(self._entries)


class ProxyRunner:
    def __init__(self, log_buffer: LogBuffer, log_handler: LogHandler | None = None):
        self._log_buffer = log_buffer
        self._log_handler = log_handler or log_buffer.add
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_started: float | None = None
        self._last_finished: float | None = None

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._last_started = time.time()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True

    def _run(self) -> None:
        try:
            run_workflow(self._log_handler)
        finally:
            with self._lock:
                self._running = False
                self._last_finished = time.time()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "last_started": self._last_started,
                "last_finished": self._last_finished,
            }


def persist_results(working: List[dict]) -> None:
    try:
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(working, f, indent=2)
    except IOError as exc:
        print(f"Error saving results to {OUTPUT_FILE}: {exc}")
        print("Printing working proxies to stdout as backup:")
        print(json.dumps(working, indent=2))


def run_workflow(log: LogHandler) -> List[dict]:
    log("Scraping proxies...")
    proxies = get_proxies()
    log(f"Total proxies found: {len(proxies)}")

    working: List[dict[str, float]] = []
    for proxy in proxies:
        is_working, latency = test_proxy(proxy)
        if is_working and latency is not None:
            working.append({"proxy": proxy, "latency": round(latency, 3)})
            log(f"[OK] {proxy} - {latency:.3f}s")
        else:
            log(f"[FAIL] {proxy}")

    persist_results(working)

    log("Summary:")
    log(f"Working proxies: {len(working)}")
    log(f"Results saved to {OUTPUT_FILE}")
    return working


def create_app(autostart: bool = True) -> Flask:
    log_buffer = LogBuffer()

    def log_message(message: str) -> None:
        log_buffer.add(message)
        print(message, flush=True)

    runner = ProxyRunner(log_buffer, log_handler=log_message)

    if autostart:
        runner.start()

    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        return render_template_string(
            """
            <!doctype html>
            <html lang=\"en\">
            <head>
              <meta charset=\"utf-8\">
              <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
              <title>Iran Proxy Finder</title>
              <style>
                body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; background: #f7f7f7; color: #1f2937; }
                h1 { color: #0f172a; }
                button { padding: 0.7rem 1.4rem; background: #0ea5e9; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; }
                button:disabled { background: #94a3b8; cursor: not-allowed; }
                .card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }
                pre { background: #0b172a; color: #e2e8f0; padding: 1rem; border-radius: 8px; max-height: 450px; overflow-y: auto; white-space: pre-wrap; }
                .status { margin-left: 1rem; font-weight: bold; }
                .pill { display: inline-block; padding: 0.3rem 0.8rem; border-radius: 999px; }
                .pill.running { background: #d1fae5; color: #047857; }
                .pill.idle { background: #f3f4f6; color: #1f2937; }
                .summary { margin-top: 1rem; color: #334155; }
              </style>
            </head>
            <body>
              <h1>Iran Proxy Finder</h1>
              <div class=\"card\">
                <p>Start a new scan to fetch, test, and save working Iranian proxies. Logs will appear below in real time.</p>
                <div>
                  <button id=\"start-btn\" onclick=\"startScan()\">Start Scan</button>
                  <span id=\"status-pill\" class=\"pill idle\">Idle</span>
                </div>
                <div class=\"summary\" id=\"summary\">Waiting to start...</div>
              </div>
              <div class=\"card\" style=\"margin-top: 1rem;\">
                <h3>Logs</h3>
                <pre id=\"logs\"></pre>
              </div>
              <script>
                const startButton = document.getElementById('start-btn');
                const logsPre = document.getElementById('logs');
                const statusPill = document.getElementById('status-pill');
                const summary = document.getElementById('summary');

                async function fetchLogs() {
                  const res = await fetch('/logs');
                  const data = await res.json();
                  logsPre.textContent = data.logs.join('\n');
                }

                async function refreshStatus() {
                  const res = await fetch('/status');
                  const data = await res.json();
                  if (data.running) {
                    statusPill.textContent = 'Running';
                    statusPill.className = 'pill running';
                    startButton.disabled = true;
                    summary.textContent = 'Scanning proxies...';
                  } else {
                    statusPill.textContent = 'Idle';
                    statusPill.className = 'pill idle';
                    startButton.disabled = false;
                    summary.textContent = data.last_finished ?
                      `Last run finished at ${new Date(data.last_finished * 1000).toLocaleString()}` :
                      'Waiting to start...';
                  }
                }

                async function startScan() {
                  startButton.disabled = true;
                  const res = await fetch('/start', { method: 'POST' });
                  if (!res.ok) {
                    const msg = await res.text();
                    alert(msg || 'Unable to start scan');
                  }
                  await refreshStatus();
                }

                async function refreshResults() {
                  await fetchLogs();
                  await refreshStatus();
                }

                refreshResults();
                setInterval(refreshResults, 2500);
              </script>
            </body>
            </html>
            """,
        )

    @app.route("/start", methods=["POST"])
    def start_scan():
        started = runner.start()
        if not started:
            return "Scan already running", 409
        return "Started", 202

    @app.route("/logs")
    def logs():  # type: ignore[override]
        return jsonify({"logs": log_buffer.snapshot()})

    @app.route("/status")
    def status():
        return jsonify(runner.status())

    @app.route("/results")
    def results():
        if OUTPUT_FILE.exists():
            with OUTPUT_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        return jsonify({"results": data})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run proxy workflow")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the workflow once in CLI mode instead of starting the web UI",
    )
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="Disable automatic scan on server start",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Flask host")
    parser.add_argument("--port", type=int, default=5000, help="Flask port")
    args = parser.parse_args()

    if args.once:
        run_workflow(print)
        return

    app = create_app(autostart=not args.no_autostart)
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
