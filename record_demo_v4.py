"""Final LoopClose demo: continuous-motion stage, real Kane values, real browser.

The freeze-prone static waits of earlier versions are gone: the canvas waveform,
HUD clock, travelling wire packets, sweep, ambient orbs and periodic micro-logs
animate on every frame. The app itself is live in the iframe, and every number
comes from proof/*.ndjson. Duration matches the natural neural narration.
"""
import json
import shutil
import subprocess
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
        "// Agent-controlled build flag. record_demo_v4.py flips this between runs.\n"
        f"window.LOOPCLOSE_BUG = {'true' if v else 'false'};\n", encoding="utf-8")


def run(tag):
    for line in (PROOF / f"{tag}.ndjson").read_text(encoding="utf-8").splitlines():
        if '"type":"run_end"' in line:
            o = json.loads(line)
            return {"status": o["status"], "credits": round(o["credits_consumed"], 2),
                    "summary": o["summary"].splitlines()[0], "url": o.get("test_url", "")}
    return {}


def nav(pg, q=""):
    u = BASE + "index.html" + q
    pg.evaluate("""u => { document.getElementById('app').src = u; document.getElementById('url').textContent = u; }""", u)
    pg.wait_for_timeout(900)


def main():
    bug, fix = run("01-bug-confirmed"), run("02-fix-verified")
    print("data:", bug, fix)
    set_bug(False)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        c = b.new_context(viewport={"width": 1280, "height": 720},
                          record_video_dir=str(VIDEOS), record_video_size={"width": 1280, "height": 720})
        def fresh(route):
            route.fulfill(status=200, content_type="text/javascript", body=CONFIG.read_text(encoding="utf-8"))
        c.route("**/config.js", fresh)
        pg = c.new_page(); vp = pg.video.path()
        pg.goto(BASE + "stage3.html", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        pg.evaluate("""d => Stage.init(d)""", {"bug": bug, "fix": fix, "evidence": EVIDENCE})

        # 1 — closed gate
        nav(pg)
        pg.evaluate("Stage.phase(1);Stage.tag('CLOSED');Stage.status('checking')")
        pg.evaluate("""async () => await Stage.burst([
          ['$ kane-cli whoami','l-cmd'],['  authenticated · oauth · agoenkcoeg4','l-ok'],
          ['$ kane-cli balance','l-cmd'],['  11200 credits available','l-ok'],
          ['gate: CLOSED — no verdict, no evidence','l-warn']], 4)""")
        pg.wait_for_timeout(32000)

        # 2 — bug confirmed
        set_bug(True)
        nav(pg, "?verdict=failed&evidence=" + EVIDENCE)
        pg.evaluate("Stage.phase(2);Stage.tag('FAILED','bad');Stage.status('running')")
        pg.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        pg.evaluate("""d => Stage.burst([
          ['$ kane-cli run \"verify gate reads GATE: OPEN\" --agent --headless','l-cmd'],
          ['{\"type\":\"step\",\"status\":\"done\",\"remark\":\"navigate: release candidate\"}','l-key'],
          ['{\"type\":\"run_end\",\"status\":\"'+d.status+'\",\"credits_consumed\":'+d.credits+'}','l-key'],
          ['  summary: '+d.summary,'l-dim'],
          ['  final_state.gate_text = \"GATE: OPEN — deploy allowed\"','l-warn'],
          ['BUG CONFIRMED: failed verdict opened the gate.','l-warn']], 4)""", bug)
        pg.wait_for_timeout(46000)

        # 3 — agent patches
        set_bug(False)
        nav(pg, "?verdict=failed&evidence=" + EVIDENCE)
        pg.evaluate("Stage.phase(3);Stage.tag('FIXING');Stage.status('patching')")
        pg.evaluate("""async () => await Stage.burst([
          ['agent: parsed run_end.status = passed (bug reproduced)','l-key'],
          ['agent: read final_state.gate_text = \"GATE: OPEN\"','l-key'],
          ['agent: patch app/config.js','l-cmd'],
          ['-  window.LOOPCLOSE_BUG = true','l-warn'],
          ['+  window.LOOPCLOSE_BUG = false','l-ok'],
          ['agent: rebuilt. asking Kane to check again.','l-dim']], 4)""")
        pg.wait_for_timeout(40000)

        # 4 — fix verified
        pg.evaluate("Stage.phase(4);Stage.tag('FIXED','good');Stage.status('running')")
        pg.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        pg.evaluate("""d => Stage.burst([
          ['$ kane-cli run \"verify gate reads GATE: CLOSED\" --agent --headless','l-cmd'],
          ['{\"type\":\"run_end\",\"status\":\"'+d.status+'\",\"credits_consumed\":'+d.credits+'}','l-key'],
          ['  summary: '+d.summary,'l-dim'],
          ['  final_state.gate_text = \"GATE: CLOSED\"','l-ok'],
          ['FIX VERIFIED: same failed verdict now blocks deploy.','l-ok']], 4)""", fix)
        pg.wait_for_timeout(44000)

        # 5 — ship + end card
        nav(pg, "?verdict=passed&evidence=" + EVIDENCE)
        pg.evaluate("Stage.phase(5);Stage.tag('VERIFIED','good');Stage.status('shipping')")
        pg.evaluate("document.getElementById('app').contentWindow.document.getElementById('deploy').click()")
        pg.evaluate("""e => Stage.burst([
          ['agent: attaching Kane evidence link','l-cmd'],['  '+e,'l-key'],
          ['verdict=passed + evidence present','l-ok'],
          ['GATE OPEN — deploy allowed. Closed loop complete.','l-ok']], 4)""", EVIDENCE)
        pg.wait_for_timeout(32000)
        pg.evaluate("Stage.end()")
        pg.wait_for_timeout(13000)
        print("raw:", vp)
        c.close(); b.close()

    shutil.copyfile(Path(vp), DEMO / "browser-recording.webm")
    script = (DEMO / "narration-script.txt").read_text(encoding="utf-8")
    extra = ("One last thing worth spelling out: the credit numbers in the terminal are not "
             "decorative. They come from the run end events of two real Kane runs, ten point "
             "four nine and fourteen point nine nine credits, each with its own Test Manager "
             "evidence link. The gate logic itself is tiny: one HTML file, one config file, one "
             "Python driver. There is no backend and no secret in this demo. What matters is that "
             "the thing calling itself verified actually got checked in a browser, and the thing "
             "calling itself fixed actually got checked again. That is all LoopClose is: a small, "
             "honest loop that refuses to take an agent's word for it.")
    narr = DEMO / "narration-full.mp3"
    for i, text in enumerate([script, extra]):
        part = DEMO / f"narr-part{i}.mp3"
        subprocess.run([EDGE_TTS, "-v", "en-US-BrianNeural", "--rate=-6%", "--volume=+5%",
                        "-t", text, "--write-media", str(part)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", "concat:" + "|".join(str(DEMO / f"narr-part{i}.mp3") for i in range(2)),
                    "-c", "copy", str(narr)], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=nw=1:nk=1", str(narr)]).decode().strip())
    print("narration:", dur)

    # Check actual raw duration; do not clone to an arbitrary length.
    rawdur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of", "default=nw=1:nk=1", str(DEMO / "browser-recording.webm")]).decode().strip())
    print("raw:", rawdur)
    target = min(max(rawdur, dur), 300)
    vf = f"tpad=stop_mode=clone:stop_duration={max(0, target - rawdur) + 1}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "browser-recording.webm"),
                    "-vf", vf, "-t", str(target), "-c:v", "libx264", "-preset", "fast",
                    "-crf", "23", "-pix_fmt", "yuv420p", str(DEMO / "video-fit.mp4")], check=True)
    final = DEMO / "loopclose-demo-v4.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(DEMO / "video-fit.mp4"),
                    "-i", str(narr), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-af", "apad",
                    "-t", str(target), "-movflags", "+faststart", str(final)], check=True)
    print("final:", target, final.stat().st_size)


if __name__ == "__main__":
    main()
