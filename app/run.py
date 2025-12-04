import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List

from flask import Flask, jsonify, render_template, request, send_from_directory

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
ASSET_IMG_DIR = Path(__file__).parent / "assets" / "img"

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
        self._stop_event: threading.Event | None = None
        self._stopping: bool = False

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._last_started = time.time()
            self._stop_event = threading.Event()
            self._stopping = False
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True

    def _run(self) -> None:
        try:
            run_workflow(self._log_handler, self._stop_event)
        finally:
            with self._lock:
                self._running = False
                self._last_finished = time.time()
                self._stop_event = None
                self._stopping = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def stop(self) -> bool:
        with self._lock:
            if not self._running or self._stop_event is None:
                return False
            self._stop_event.set()
            self._stopping = True
            return True

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "last_started": self._last_started,
                "last_finished": self._last_finished,
                "stopping": self._stopping,
            }


def persist_results(working: List[dict]) -> None:
    try:
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(working, f, indent=2)
    except IOError as exc:
        print(f"Error saving results to {OUTPUT_FILE}: {exc}")
        print("Printing working proxies to stdout as backup:")
        print(json.dumps(working, indent=2))


def run_workflow(
    log: LogHandler, stop_event: threading.Event | None = None
) -> List[dict]:
    log("Scraping proxies...")
    proxies = get_proxies()
    log(f"Total proxies found: {len(proxies)}")

    max_workers_env = os.environ.get("MAX_WORKERS")
    max_workers = 20
    if max_workers_env:
        try:
            val = int(max_workers_env)
            if val > 0:
                max_workers = val
        except ValueError:
            log(f"Warning: MAX_WORKERS ('{max_workers_env}') is not a valid integer. Using default value {max_workers}.")
    log(f"Using up to {max_workers} concurrent workers")

    max_env = os.environ.get("MAX_PROXIES")
    if max_env:
        try:
            limit = int(max_env)
            if limit > 0:
                proxies = proxies[:limit]
                log(f"Testing first {len(proxies)} proxies due to MAX_PROXIES")
        except ValueError:
            pass

    targets_env = os.environ.get("TARGET_URLS")
    if targets_env:
        targets = [t.strip() for t in targets_env.split(",") if t.strip()]
    else:
        single = os.environ.get("TARGET_URL")
        if single:
            targets = [single]
        else:
            targets = [
                "https://api.ipify.org?format=json",
                "https://httpbin.org/get",
                "https://icanhazip.com",
            ]

    per_target_limit_env = os.environ.get("MAX_PER_TARGET")
    per_target_limit: int | None = None
    if per_target_limit_env:
        try:
            val = int(per_target_limit_env)
            if val > 0:
                per_target_limit = val
        except ValueError:
            pass

    working: List[dict] = []
    for target in targets:
        if stop_event is not None and stop_event.is_set():
            break
        log(f"Testing target: {target}")
        proxies_to_test = proxies[:per_target_limit] if per_target_limit else proxies
        if not proxies_to_test:
            continue

        def worker(p: str) -> tuple[str, bool, float | None, str | None]:
            if stop_event is not None and stop_event.is_set():
                return p, False, None, None
            is_working, latency, scheme = test_proxy(p, target_url=target)
            return p, is_working, latency, scheme

        pool_size = min(max_workers, len(proxies_to_test))
        executor = ThreadPoolExecutor(max_workers=pool_size)
        futures = [executor.submit(worker, proxy) for proxy in proxies_to_test]
        try:
            for future in as_completed(futures):
                if stop_event is not None and stop_event.is_set():
                    break
                try:
                    proxy, is_working, latency, scheme = future.result()
                except Exception as e:
                    log(f"[ERROR] Unexpected error testing proxy: {e}")
                    continue
                if is_working and latency is not None:
                    working.append(
                        {
                            "proxy": proxy,
                            "latency": round(latency, 3),
                            "scheme": scheme,
                            "target": target,
                        }
                    )
                    log(f"[OK] {proxy} via {scheme} - {latency:.3f}s")
                else:
                    log(f"[FAIL] {proxy}")
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    persist_results(working)

    if stop_event is not None and stop_event.is_set():
        log("Stopped")
    log("Summary:")
    log(f"Working proxies: {len(working)}")
    log(f"Results saved to {OUTPUT_FILE}")
    return working


def create_app(autostart: bool = False) -> Flask:
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
        return render_template("index.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            str(ASSET_IMG_DIR),
            "iran-proxy-finder.ico",
            mimetype="image/x-icon",
        )

    @app.route("/assets/img/<path:filename>")
    def serve_img(filename: str):
        return send_from_directory(str(ASSET_IMG_DIR), filename)

    @app.route("/start", methods=["POST"])
    def start_scan():
        data = request.get_json(silent=True) or {}
        targets = data.get("targets")
        if isinstance(targets, list) and targets:
            os.environ["TARGET_URLS"] = ",".join(str(t) for t in targets)
        else:
            os.environ.pop("TARGET_URLS", None)
        max_proxies = data.get("max_proxies")
        if max_proxies is not None:
            try:
                val = int(max_proxies)
                if val > 0:
                    os.environ["MAX_PROXIES"] = str(val)
                else:
                    os.environ.pop("MAX_PROXIES", None)
            except (TypeError, ValueError):
                os.environ.pop("MAX_PROXIES", None)
        else:
            os.environ.pop("MAX_PROXIES", None)

        max_per_target = data.get("max_per_target")
        if max_per_target is not None:
            try:
                val = int(max_per_target)
                if val > 0:
                    os.environ["MAX_PER_TARGET"] = str(val)
                else:
                    os.environ.pop("MAX_PER_TARGET", None)
            except (TypeError, ValueError):
                os.environ.pop("MAX_PER_TARGET", None)
        else:
            os.environ.pop("MAX_PER_TARGET", None)
        started = runner.start()
        if not started:
            return "Scan already running", 409
        return "Started", 202

    @app.route("/stop", methods=["POST"])
    def stop_scan():
        stopped = runner.stop()
        if not stopped:
            return "No scan running", 409
        return "Stopping", 202

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
        "--autostart",
        action="store_true",
        help="Enable automatic scan on server start",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Flask host")
    parser.add_argument("--port", type=int, default=5000, help="Flask port")
    args = parser.parse_args()

    if args.once:
        run_workflow(print)
        return

    app = create_app(autostart=(args.autostart or os.environ.get("AUTOSTART") == "1"))
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
