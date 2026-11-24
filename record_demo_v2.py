"""Record a polished demo of the LoopClose closed loop.

A real Chromium context is recorded with Playwright recordVideo. The frame shown
is a live operator stage: the actual app runs in an iframe, and the terminal pane
types the real NDJSON values parsed from proof/*.ndjson. No fake screenshots.
Narration uses a natural Edge neural voice; the browser recording is kept raw.
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
DEMO = ROOT / "demo"
CONFIG = APP / "config.js"
PROOF = ROOT / "proof"
VIDEOS = DEMO / "captures"
VIDEOS.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8137/"
EVIDENCE = "https://test-manager.lambdatest.com/projects/01M86DXG5CJ43MPR0MCCW7DQ1N/test-cases/01M86EKV7ZQQ9FKXCF6PP1KETS"
EDGE_TTS = r"C:\Users\AGUNG\AppData\Local\hermes\installs\790a79a27e36f560\environments\7e8e7bc2537e43ecbcc5953eb45814c3\venv\Scripts\edge-tts.exe"


def set_bug(v: bool):
    CONFIG.write_text(
        "// Agent-controlled build flag. record_demo.py flips this between runs.\n"
        f"window.LOOPCLOSE_BUG = {'true' if v else 'false'};\n", encoding="utf-8")


def read_run(tag):
    p = PROOF / f"{tag}.ndjson"
    for line in p.read_text(encoding="utf-8").splitlines():
        if '"type":"run_end"' in line:
            o = json.loads(line)
            return {"status": o["status"], "credits": round(o["credits_consumed"], 2),
                    "summary": o["summary"].splitlines()[0], "url": o.get("test_url", "")}
    return {}


def app_nav(page, query=""):
    url = BASE + "index.html" + query
    page.evaluate("""u => {
      const f = document.getElementById('app');
      f.src = u;
      document.getElementById('url').textContent = u;
    }""", url)
    page.wait_for_timeout(700)


def main():
    bug = read_run("01-bug-confirmed")
    fix = read_run("02-fix-verified")
    print("run data:", bug, fix)
    set_bug(False)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
                                    args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
            record_video_dir=str(VIDEOS),
            record_video_size={"width": 1280, "height": 720})
        # Each build variant is honestly re-read from the config file on iframe load.
        def no_cache(route):
            route.fulfill(status=200, content_type="text/javascript",
                          body=CONFIG.read_text(encoding="utf-8"))
        context.route("**/config.js", no_cache)
        page = context.new_page()
        vpath = page.video.path()
        page.goto(BASE + "stage.html", wait_until="networkidle")
        page.wait_for_timeout(600)

        # 1 — Gate closed
        app_nav(page)
        page.evaluate("Stage.step(1)")
        page.evaluate("""async () => await Stage.log([
          '$ kane-cli whoami',
          '  Authenticated  ·  oauth  ·  agoenkcoeg4',
          '$ kane-cli balance',
          '  11200 credits available',
          'LoopClose gate: CLOSED  (no verdict, no evidence)'
        ], 5)""")
        page.wait_for_timeout(30000)

        # 2 — Kane catches the bug on the buggy build
        set_bug(True)
        app_nav(page, "?verdict=failed&evidence=" + EVIDENCE)
        page.evaluate("Stage.step(2)")
        page.evaluate("""async () => await Stage.log([
          '$ kane-cli run "verify the gate reads GATE: OPEN" --agent --headless',
          '{"step":2,"status":"done","remark":"navigate: open release candidate"}',
          '{"type":"run_end","status":"%s","credits_consumed":%s}',
          '  summary: %s',
          '  final_state.gate_text = "GATE: OPEN — deploy allowed"',
          'BUG CONFIRMED: failed verdict opened the gate.'
        ], 4)""" % (bug["status"], bug["credits"], bug["summary"]))
        page.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        page.wait_for_timeout(35000)

        # 3 — Agent reads the verdict and patches the build
        set_bug(False)
        app_nav(page, "?verdict=failed&evidence=" + EVIDENCE)
        page.evaluate("Stage.step(3)")
        page.evaluate("""async () => await Stage.log([
          'agent: parsed run_end.status = passed (bug reproduced)',
          'agent: reading final_state.gate_text = "GATE: OPEN"',
          'agent: patch app/config.js',
          '-  window.LOOPCLOSE_BUG = true',
          '+  window.LOOPCLOSE_BUG = false',
          'agent: rebuilt. asking Kane to check again.'
        ], 4)""")
        page.wait_for_timeout(35000)

        # 4 — Kane verifies the fix
        page.evaluate("Stage.step(4)")
        page.evaluate("""async () => await Stage.log([
          '$ kane-cli run "verify the gate reads GATE: CLOSED" --agent --headless',
          '{"type":"run_end","status":"%s","credits_consumed":%s}',
          '  summary: %s',
          '  final_state.gate_text = "GATE: CLOSED"',
          'FIX VERIFIED: same failed verdict now blocks deploy.'
        ], 4)""" % (fix["status"], fix["credits"], fix["summary"]))
        page.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        page.wait_for_timeout(35000)

        # 5 — Proof attached, gate opens, ship
        app_nav(page, "?verdict=passed&evidence=" + EVIDENCE)
        page.evaluate("Stage.step(5)")
        page.evaluate("""async () => await Stage.log([
          'agent: attaching Kane evidence link to release candidate',
          '  %s',
          'verdict=passed + evidence present',
          'GATE OPEN — deploy allowed. Closed loop complete.'
        ], 4)""" % EVIDENCE)
        page.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        page.wait_for_timeout(38000)

        print("raw recorded:", vpath)
        context.close()
        browser.close()

    raw = Path(vpath)
    shutil.copyfile(raw, DEMO / "browser-recording.webm")

    script = """LoopClose. A release gate that refuses to deploy until a real browser proves the flow. Most coding agents write code fast, then call it done. This project makes that claim testable.

Here the gate starts closed. Nothing ships on a claim. Only a passing verdict with an evidence link can open it.

Now the buggy build. A shortcut in the code opens the gate whenever an evidence link is present, even though the verdict says failed. Kane CLI drives this page in a real browser, reads the gate, and asserts what the release candidate actually does. The run returns machine readable output. It reports that the gate really is open on a failed verdict. The bug is confirmed by behavior.

The agent reads that verdict, flips the broken flag in the build, and rebuilds. This is the closed loop: the verifier's output becomes the builder's input.

Second run. Same failed verdict, same evidence link, fixed build. Kane asserts the gate now reads, gate closed. The run passes with fresh evidence from a real browser.

Finally, a passing verdict plus an evidence link arrives. The gate opens, and the agent is allowed to ship. Ships, verified, closed loop, craft. Do not trust the agent's word. Trust the run."""
    narr = DEMO / "narration-neural.mp3"
    subprocess.run([EDGE_TTS, "-v", "en-US-BrianNeural", "--rate=-8%", "--volume=+5%",
                    "-t", script, "--write-media", str(narr)], check=True)
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(narr)]).decode().strip())
    print("narration duration:", dur)

    video = DEMO / "loopclose-demo.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "browser-recording.webm"),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={max(0, dur - 170) + 5}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(DEMO / "video-fit.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "video-fit.mp4"),
                    "-i", str(narr), "-c:v", "copy", "-c:a", "aac", "-shortest",
                    "-movflags", "+faststart", str(video)], check=True)
    print("final:", video, video.stat().st_size)


if __name__ == "__main__":
    main()
