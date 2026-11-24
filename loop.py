#!/usr/bin/env python3
"""LoopClose: agent <-> Kane closed-loop demonstration.

Workflow:
  1. Build the buggy variant (config.js: LOOPCLOSE_BUG = true).
  2. Kane runs a browser assertion against the app: a FAILED verdict must keep
     the gate CLOSED. Kane PASSES the run iff it observes the bug (gate OPEN).
  3. The agent reads the NDJSON verdict. If Kane "passed", the bug is confirmed:
     the agent patches config.js to false and asks Kane to run again.
  4. Second Kane run expects gate CLOSED. A passing run means the fix holds.

All Kane runs use --agent (NDJSON), and evidence links are extracted from the
final run_end event. This is the closed loop the hackathon judges score.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
PROOF = ROOT / "proof"
CONFIG = APP / "config.js"
PROOF.mkdir(exist_ok=True)

URL = "http://127.0.0.1:8137/?verdict=failed&evidence=https%3A%2F%2Fexample.com%2Fproof"
DEFAULT_BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")


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


def build_env() -> dict:
    env = dict(os.environ, KANE_CLI_USER_AGENT=os.environ.get("KANE_CLI_USER_AGENT", "hermes"))
    if not env.get("KANE_CLI_CHROME_PATH") and DEFAULT_BRAVE.exists():
        env["KANE_CLI_CHROME_PATH"] = str(DEFAULT_BRAVE)
    return env


def check_local_server(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def set_variant(buggy: bool):
    CONFIG.write_text(
        "// Agent-controlled build flag. loop.py flips this between runs.\n"
        f"window.LOOPCLOSE_BUG = {'true' if buggy else 'false'};\n",
        encoding="utf-8")
    print(f"[agent] build variant: {'BUGGY' if buggy else 'FIXED'}")


def kane_run(kane_bin: str, env: dict, expect: str, tag: str) -> dict:
    objective = (f"Go to {URL} and verify the release gate text shows "
                 f"{expect}. Answer only what the gate text reads.")
    outfile = PROOF / f"{tag}.ndjson"
    print(f"[kane] running: expect {expect} ...")
    with outfile.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            [kane_bin, "run", objective, "--agent", "--headless",
             "--timeout", "240", "--name", tag],
            cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT,
            timeout=360)
    lines = [l for l in outfile.read_text(encoding="utf-8").splitlines()
             if l.strip().startswith("{")]
    end = None
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "run_end":
            end = obj
    if end is None:
        print(f"[kane] no run_end; exit={proc.returncode}")
        return {"status": "no-run", "exit": proc.returncode, "file": str(outfile)}
    print(f"[kane] status={end['status']} credits={end['credits_consumed']:.2f}")
    print(f"[kane] evidence: {end.get('test_url', 'none')}")
    end["_file"] = str(outfile)
    return end


def main():
    if not check_local_server(URL.split("?")[0]):
        print("Local app is not running. Start: python -m http.server 8137 --directory app")
        sys.exit(2)

    kane_bin = resolve_kane()
    env = build_env()

    set_variant(True)
    bug = kane_run(kane_bin, env, "GATE: OPEN — deploy allowed", "01-bug-confirmed")
    confirmed = bug.get("status") == "passed"
    print(f"[agent] bug confirmed by Kane: {confirmed}")

    if not confirmed:
        print("[agent] Kane did not reproduce the bug; nothing to fix.")
        return

    set_variant(False)
    fix = kane_run(kane_bin, env, "GATE: CLOSED", "02-fix-verified")
    if fix.get("status") == "passed":
        print("[agent] fix verified by Kane. Loop closed. Evidence:")
        print(f"  bug: {bug.get('test_url')}")
        print(f"  fix: {fix.get('test_url')}")
    else:
        print("[agent] fix not verified — keeping gate closed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
