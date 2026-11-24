from playwright.sync_api import sync_playwright
from pathlib import Path
p = Path(r'F:\hermes\loopclose\demo\captures')
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    c = b.new_context(viewport={'width': 1280, 'height': 720},
                      record_video_dir=str(p), record_video_size={'width': 1280, 'height': 720})
    pg = c.new_page()
    v = pg.video.path()
    pg.goto('http://127.0.0.1:8137/stage3.html', wait_until='networkidle')
    pg.evaluate("Stage.init({bug:{status:'passed',credits:10.49,summary:''},fix:{status:'passed',credits:14.99,summary:''},evidence:'x'})")
    pg.wait_for_timeout(12000)
    c.close()
    b.close()
    print(v)
