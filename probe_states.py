from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    pg=b.new_page(viewport={'width':1000,'height':700})
    for name,q in [('closed',''),('bug','?verdict=failed&evidence=x'),('fixed','?verdict=failed'),('proof','?verdict=passed&evidence=x')]:
        pg.goto('http://127.0.0.1:8137/index.html'+q,wait_until='networkidle')
        pg.wait_for_timeout(500)
        print(name, pg.evaluate("({cls:document.body.className,banner:document.getElementById('banner').textContent,gate:document.getElementById('gate').textContent})"))
        pg.screenshot(path=f'demo/state_v4_{name}.png')
    b.close()
