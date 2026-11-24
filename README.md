# LoopClose

A deploy gate that refuses to ship until a real browser proves the flow. The coding agent fixes what Kane catches, Kane checks again, and the verdict travels back to the agent as machine-readable NDJSON. The loop is the product.

## The loop

```
agent builds buggy variant
        ↓
Kane CLI opens the real app in Chrome/Brave, asserts the gate
        ↓  --agent NDJSON + evidence link
agent reads verdict → flips the broken flag → rebuilds
        ↓
Kane CLI runs again → passing verdict + evidence link
        ↓
deploy allowed
```

## Run it

```bash
# terminal 1: serve the app
python -m http.server 8137 --directory app

# terminal 2: run the closed loop
python loop.py
```

`loop.py` writes two real Kane runs into `proof/`:

1. `01-bug-confirmed.ndjson` — the buggy build lets a failed verdict open the gate. Kane's assertion that the gate reads `GATE: OPEN` passes, which confirms the bug.
2. `02-fix-verified.ndjson` — the agent flips `app/config.js` to the fixed build; Kane's assertion that the gate reads `GATE: CLOSED` passes, which confirms the fix.

Both runs upload evidence to Test Manager and print their `test_url` links.

One-off Kane run:

```bash
export KANE_CLI_CHROME_PATH="C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
KANE_CLI_USER_AGENT=hermes kane-cli run \
  "Go to http://127.0.0.1:8137/?verdict=failed&evidence=https://example.com/proof and verify the gate text shows GATE: CLOSED" \
  --agent --headless --timeout 240
```

## Why this fits the challenge

- **Ships:** the gate is a real, usable flow, not a slide.
- **Verified:** Kane catches a real security regression (failed verdict opening the gate) and then proves the fix.
- **Closed loop:** the agent parses Kane's `run_end` verdict and changes the build in response; Kane re-verifies. `loop.py` is the loop.
- **Craft:** no backend, no secrets, no framework. `index.html` + `config.js` + one Python driver.

## Files

| Path | Role |
|---|---|
| `app/index.html` | the release gate UI and its verdict logic |
| `app/config.js` | agent-controlled build flag (`LOOPCLOSE_BUG`) |
| `app/stage.html` | live operator stage: real app in an iframe + typed real NDJSON |
| `loop.py` | agent driver: build → Kane → read verdict → fix → Kane |
| `record_demo_v2.py` | Playwright `recordVideo` driver for `demo/loopclose-demo.mp4` |
| `proof/*.ndjson` | real Kane run output with evidence links |
| `demo/browser-recording.webm` | raw browser recording (before music/narration) |
| `demo/` | final demo video and narration |
