"""Record a real browser demo of the LoopClose closed loop.

Uses Playwright's recordVideo (real browser context, real clicks, real reloads),
then muxes a natural Edge neural voice narration into an MP4.
The terminal overlay shows values parsed from the actual proof/*.ndjson files.
"""
import json
import re
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


def overlay(page, title, lines, color="#c7d2fe"):
    page.evaluate("""([title, lines, color]) => {
      let old = document.getElementById('kane-overlay'); if (old) old.remove();
      const d = document.createElement('div'); d.id='kane-overlay';
      d.style.cssText = 'position:fixed;right:22px;bottom:22px;width:410px;background:#080b11ee;border:1px solid '+color+';border-radius:12px;padding:14px 16px;color:#dbe4ff;font:12px/1.55 Consolas,monospace;z-index:9999;box-shadow:0 10px 40px #0008';
      d.innerHTML = '<div style="color:'+color+';font-weight:700;margin-bottom:8px">'+title+'</div>' + lines.map(x=>'<div>'+x.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</div>').join('');
      document.body.appendChild(d);
    }""", [title, lines, color])


def main():
    bug = read_run("01-bug-confirmed")
    fix = read_run("02-fix-verified")
    print("run data:", bug, fix)
    set_bug(False)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEOS),
            record_video_size={"width": 1280, "height": 720})
        # Serve the real, current config.js with no caching so each build is honest.
        def no_cache(route):
            route.fulfill(status=200, content_type="text/javascript",
                          body=CONFIG.read_text(encoding="utf-8"))
        context.route("**/config.js", no_cache)
        page = context.new_page()
        vpath = page.video.path()

        # 0:00 intro / closed gate
        page.goto(BASE, wait_until="networkidle")
        overlay(page, "LOOPCLOSE / AGENT + KANE", [
            "The gate stays closed until a real browser proves the flow.",
            "No claim. No screenshot in chat. A machine-readable verdict.",
        ])
        time.sleep(16)

        # 0:16 buggy build + failed verdict + deploy request
        set_bug(True)
        page.goto(BASE + "?verdict=failed&evidence=" + EVIDENCE, wait_until="networkidle")
        overlay(page, "BUILD: BUGGY  /  KANE RUN 01", [
            "$ kane-cli run ... --agent --headless",
            f"run_end status={bug.get('status')} credits={bug.get('credits')}",
            f"{bug.get('summary')}",
            "The failed verdict still opened the gate. Bug confirmed.",
        ], "#fb7185")
        page.locator("#deploy").click()
        time.sleep(17)

        # 0:33 agent reads verdict and flips flag
        set_bug(False)
        page.reload(wait_until="networkidle")
        overlay(page, "AGENT ACTION / READ VERDICT -> PATCH BUILD", [
            "Parsed run_end.status = passed (bug reproduced).",
            "Edited app/config.js: LOOPCLOSE_BUG true -> false.",
            "Rebuilt. Ask Kane to check again.",
        ], "#818cf8")
        time.sleep(17)

        # 0:50 fixed build still blocks on failed verdict
        overlay(page, "BUILD: FIXED  /  KANE RUN 02", [
            f"run_end status={fix.get('status')} credits={fix.get('credits')}",
            f"{fix.get('summary')}",
            "Same failed verdict now keeps the gate CLOSED.",
        ], "#4ade80")
        page.locator("#deploy").click()
        time.sleep(18)

        # 1:08 passing proof unlocks deploy
        page.goto(BASE + "?verdict=passed&evidence=" + EVIDENCE, wait_until="networkidle")
        overlay(page, "PROOF ATTACHED / DEPLOY ALLOWED", [
            "verdict=passed + evidence link present",
            "Kane evidence: Test Manager case with screenshots and logs.",
            "The agent may ship because the verifier proved the fix.",
        ], "#4ade80")
        page.locator("#deploy").click()
        time.sleep(18)
        print("raw recorded:", vpath)
        context.close()
        browser.close()

    raw = Path(vpath)
    shutil.copyfile(raw, DEMO / "browser-recording.webm")

    # Narration: natural neural voice (Brian), generated from a clean script.
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

    # Fit the video length to the narration by cloning the last frame if needed.
    video = DEMO / "loopclose-demo.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "browser-recording.webm"),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={max(0, dur - 88) + 5}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(DEMO / "video-fit.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "video-fit.mp4"),
                    "-i", str(narr), "-c:v", "copy", "-c:a", "aac", "-shortest",
                    "-movflags", "+faststart", str(video)], check=True)
    print("final:", video, video.stat().st_size)


if __name__ == "__main__":
    main()
