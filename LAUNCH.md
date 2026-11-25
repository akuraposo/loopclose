# LoopClose — launch copy (paste-ready)

Repo: https://github.com/akuraposo/loopclose
Video: https://youtu.be/3wC081DVVkk (3:34)
Live App: https://akuraposo.github.io/loopclose/app/

## X / Twitter

Agents write code fast. Proving it works is the hard part.

Built LoopClose with Antigravity: a deploy gate that refuses to ship until @TestMuAI Kane CLI verifies the flow in a real browser. Kane caught a bug, the agent fixed it, Kane verified again. That loop is the product.

Repo + 3:34 demo: https://github.com/akuraposo/loopclose

#KaneCLIHackDay

## LinkedIn

Most AI coding agents call "done" the moment the code compiles. LoopClose makes that claim testable.

LoopClose is a release gate built with Antigravity that stays closed until Kane CLI drives the real app in a real browser and returns a passing verdict with Test Manager evidence. When Kane caught a regression — a failed verdict still opening the gate — the Python driver parsed the structured `--agent` NDJSON `run_end` event, flipped the broken build flag, served an uncached build, and asked Kane to check again. The second run passed and attached fresh evidence.

Three bars, one small project: it ships, Kane proved something, and the agent closed the loop.

Repo: https://github.com/akuraposo/loopclose
Demo: https://youtu.be/3wC081DVVkk

#KaneCLIHackDay #AIagents #Testing

## Hacker News — Show HN

Title: Show HN: LoopClose – a deploy gate that waits for Kane CLI to prove the flow in a real browser

Body:
LoopClose is a small experiment in making AI coding agents prove their work. The gate stays closed until Kane CLI runs the app in a real browser and returns a passing verdict plus a trusted Test Manager evidence link.

I seeded a regression: with the buggy build (`LOOPCLOSE_BUG = true`), a failed verdict still opened the gate. Kane caught it in headless Chrome. `loop.py` parsed the NDJSON `run_end` event, flipped `app/config.js`, served the uncached app, and ran Kane again; the gate stayed closed and the fix was verified with new evidence.

It is one static HTML file with live Guest Checkout (`WELCOME10`) and Sign Up candidate flows, one config flag, a cross-platform Python driver (`loop.py`), and a unit + Chromium E2E test suite (`test_loop.py`). Repo and 3:34 demo are linked inside.

## Reddit (r/SideProject or r/webdev)

Title: Built LoopClose: a deploy gate that blocks shipping until a real headless browser (Kane CLI) proves the fix

Body:
AI coding agents love saying "done" as soon as code compiles. I built LoopClose for the KaneCLI Online Hackathon to make the deploy gate wait for real browser verification.

How it works:
1. `loop.py` boots a local no-cache static server and sets `LOOPCLOSE_BUG = true`.
2. Kane CLI drives headless Chrome (`--agent`) and confirms the failed verdict wrongly opens the gate (`15.10` cr).
3. `loop.py` parses the NDJSON `run_end` event, patches `app/config.js`, and runs Kane again (`10.60` cr).
4. Run 3 (`--verify-open`, `10.70` cr) feeds Run 2's real Test Manager URL into `?verdict=passed` and verifies `GATE: OPEN — deploy allowed` (plus interactive Checkout `WELCOME10` and Sign Up flows).

Repo: https://github.com/akuraposo/loopclose
Live demo: https://akuraposo.github.io/loopclose/app/
Demo video (3:34): https://youtu.be/3wC081DVVkk

## YouTube description

LoopClose: a deploy gate that refuses to ship until Kane CLI proves the flow in a real browser.

The agent builds a buggy variant. Kane finds the regression, the agent reads the verdict and fixes the build, then Kane verifies again. Two real Kane runs, two evidence links, one closed loop.

0:00 What LoopClose is
0:42 Gate starts closed
1:24 Kane catches the bug
2:07 Agent fixes, Kane re-verifies
2:50 Ship

Repo: https://github.com/akuraposo/loopclose
#KaneCLIHackDay

## Submission form answers

- GitHub URL: https://github.com/akuraposo/loopclose
- About: A deploy gate that refuses to ship until Kane CLI verifies the flow in a real browser. Built with Antigravity; Kane caught a seeded regression (failed verdict opening the gate, 15.10 cr), loop.py parsed the run_end NDJSON, fixed the build flag, re-verified GATE: CLOSED (10.60 cr), and proved deploy unlock with the Test Manager link (10.70 cr). Includes interactive Checkout/Sign Up flows and 9/9 unit + Chromium E2E tests.
- Demo video: https://youtu.be/3wC081DVVkk
- Live URL: https://akuraposo.github.io/loopclose/app/
- Attachments: `demo/loopclose-thumbnail.png` + `demo/loopclose-architecture.png`
- Launch buzz: paste X, LinkedIn, Show HN, and Reddit post URLs here
