#!/usr/bin/env python3
"""LoopClose: agent <-> Kane closed-loop demonstration.

Workflow:
  1. Ensure the app is served locally (auto-starts an embedded HTTP server on
     127.0.0.1:8137 if none is running).
  2. Build the buggy variant (config.js: LOOPCLOSE_BUG = true).
  3. Kane runs a browser assertion against the app: a FAILED verdict must keep
     the gate CLOSED. Kane PASSES the run iff it observes the bug (gate OPEN).
  4. The agent parses the NDJSON run_end event. If Kane "passed", the bug is
     confirmed: the agent patches config.js back to false and calls Kane again.
  5. Second Kane run expects gate CLOSED. Always restores config.js to the
     fixed state in a finally block so failed/interrupted runs never leave a
     broken build behind.

All Kane runs use --agent (NDJSON), and evidence links are extracted from the
final run_end event.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
PROOF = ROOT / "proof"
CONFIG = APP / "config.js"
PROOF.mkdir(exist_ok=True)

DEFAULT_PORT = 8137
URL = f"http://127.0.0.1:{DEFAULT_PORT}/?verdict=failed&evidence=https%3A%2F%2Fexample.com%2Fproof"
DEFAULT_BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


class LocalAppServer:
    """Serves the static app/ directory on demand when no server is running."""

    def __init__(self, directory: Path = APP, host: str = "127.0.0.1", port: int = DEFAULT_PORT):
        self.directory = directory
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "LocalAppServer":
        handler = functools.partial(_QuietStaticHandler, directory=str(self.directory))
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def resolve_kane() -> str:
    kane = (
        os.environ.get("KANE_CLI_BIN")
        or shutil.which("kane-cli")
        or shutil.which("kane-cli.cmd")
    )
    if not kane:
        print("kane-cli not found in PATH. Install with: npm install -g @testmuai/kane-cli")
        sys.exit(2)
    return kane


def build_env() -> dict[str, str]:
    env = dict(os.environ, KANE_CLI_USER_AGENT=os.environ.get("KANE_CLI_USER_AGENT", "hermes"))
    if not env.get("KANE_CLI_CHROME_PATH") and DEFAULT_BRAVE.exists():
        env["KANE_CLI_CHROME_PATH"] = str(DEFAULT_BRAVE)
    return env


def check_local_server(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def set_variant(buggy: bool, config_path: Path = CONFIG) -> None:
    config_path.write_text(
        "// Agent-controlled build flag. loop.py flips this between runs.\n"
        f"window.LOOPCLOSE_BUG = {'true' if buggy else 'false'};\n",
        encoding="utf-8",
    )
    print(f"[agent] build variant: {'BUGGY' if buggy else 'FIXED'}")


def parse_run_end(ndjson_text: str) -> dict[str, Any] | None:
    """Extract the final run_end JSON object from Kane CLI --agent NDJSON output."""
    end = None
    for line in ndjson_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("type") == "run_end":
            end = obj
    return end


def kane_run(kane_bin: str, env: dict[str, str], target_url: str, expect: str, tag: str) -> dict[str, Any]:
    objective = (
        f"Go to {target_url} and verify the release gate text shows "
        f"{expect}. Answer only what the gate text reads."
    )
    outfile = PROOF / f"{tag}.ndjson"
    print(f"[kane] running: expect {expect} ...")
    with outfile.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            [kane_bin, "run", objective, "--agent", "--headless",
             "--timeout", "240", "--name", tag],
            cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT,
            timeout=360,
        )
    end = parse_run_end(outfile.read_text(encoding="utf-8"))
    if end is None:
        print(f"[kane] no run_end; exit={proc.returncode}")
        return {"status": "no-run", "exit": proc.returncode, "file": str(outfile)}
    credits = float(end.get("credits_consumed") or 0.0)
    print(f"[kane] status={end['status']} credits={credits:.2f}")
    print(f"[kane] evidence: {end.get('test_url', 'none')}")
    end["_file"] = str(outfile)
    return end


def run_closed_loop(verify_open: bool = False) -> int:
    kane_bin = resolve_kane()
    env = build_env()

    managed_server = None
    target_base = f"http://127.0.0.1:{DEFAULT_PORT}"
    if not check_local_server(target_base):
        managed_server = LocalAppServer(APP, port=DEFAULT_PORT)
        managed_server.__enter__()
        print(f"[server] auto-started local static server at {managed_server.base_url}")

    failed_url = f"{target_base}/?verdict=failed&evidence=https%3A%2F%2Fexample.com%2Fproof"
    try:
        set_variant(True)
        bug = kane_run(kane_bin, env, failed_url, "GATE: OPEN — deploy allowed", "01-bug-confirmed")
        confirmed = bug.get("status") == "passed"
        print(f"[agent] bug confirmed by Kane: {confirmed}")

        if not confirmed:
            print("[agent] Kane did not reproduce the bug; keeping fixed build.")
            return 1

        set_variant(False)
        fix = kane_run(kane_bin, env, failed_url, "GATE: CLOSED", "02-fix-verified")
        if fix.get("status") != "passed":
            print("[agent] fix not verified — keeping gate closed.")
            return 1

        print("[agent] fix verified by Kane. Loop closed. Evidence:")
        print(f"  bug: {bug.get('test_url')}")
        print(f"  fix: {fix.get('test_url')}")

        if verify_open and fix.get("test_url"):
            encoded_ev = urllib.parse.quote(str(fix["test_url"]), safe="")
            open_url = f"{target_base}/?verdict=passed&evidence={encoded_ev}"
            opened = kane_run(kane_bin, env, open_url, "GATE: OPEN — deploy allowed", "03-deploy-unlocked")
            if opened.get("status") != "passed":
                print("[agent] trusted proof did not unlock gate.")
                return 1
            print(f"  unlocked: {opened.get('test_url')}")
        return 0
    finally:
        # Always restore clean fixed build flag even on timeout/Ctrl+C/failure
        set_variant(False)
        if managed_server is not None:
            managed_server.__exit__(None, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="LoopClose agent <-> Kane CLI closed-loop driver")
    parser.add_argument(
        "--verify-open",
        action="store_true",
        help="Run a 3rd Kane check feeding the real Test Manager URL into ?verdict=passed to confirm deploy unlock",
    )
    args = parser.parse_args()
    sys.exit(run_closed_loop(verify_open=args.verify_open))


if __name__ == "__main__":
    main()
