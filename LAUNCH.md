# LoopClose — launch copy (paste-ready)

Repo: https://github.com/akuraposo/loopclose
Video: https://youtu.be/3wC081DVVkk
Direct video file: demo/loopclose-demo.mp4 (3:00, 1080p)

## X / Twitter

Agents write code fast. Proving it works is the hard part.

Built LoopClose: a deploy gate that refuses to ship until @TestMuAI Kane CLI verifies the flow in a real browser. Kane caught a bug, the agent fixed it, Kane verified again. That loop is the product.

Repo + 3-min demo: https://github.com/akuraposo/loopclose

#KaneCLIHackDay

## LinkedIn

Most AI coding agents call "done" the moment the code compiles. LoopClose makes that claim testable.

LoopClose is a release gate that stays closed until Kane CLI drives the real app in a real browser and returns a passing verdict with evidence. When Kane caught a regression — a failed verdict still opening the gate — the agent read the structured run output, flipped the broken build flag, and asked Kane to check again. The second run passed and attached fresh evidence.

Three bars, one small project: it ships, Kane proved something, and the agent closed the loop.

Repo: https://github.com/akuraposo/loopclose
Demo: https://youtu.be/3wC081DVVkk

#KaneCLIHackDay #AIagents #Testing

## Hacker News — Show HN

Title: Show HN: LoopClose – a deploy gate that waits for Kane CLI to prove the flow in a real browser

Body:
LoopClose is a small experiment in making AI coding agents prove their work. The gate stays closed until Kane CLI runs the app in a real browser and returns a passing verdict plus an evidence link.

I seeded a regression: with the buggy build, a failed verdict still opened the gate. Kane caught it. The agent parsed the NDJSON run_end event, flipped the build flag, and ran Kane again; the gate then stayed closed and the fix was verified with new evidence.

It is one HTML file, one config file, and a Python driver. No backend, no secrets. Repo and 3-minute demo are linked inside.

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
- About: A deploy gate that refuses to ship until Kane CLI verifies the flow in a real browser. Built with Hermes Agent; Kane caught a seeded regression (failed verdict opening the gate), the agent parsed the run_end NDJSON, fixed the build flag, and Kane re-verified. Two real runs with Test Manager evidence links.
- Demo video: https://youtu.be/3wC081DVVkk
- Live URL: https://akuraposo.github.io/loopclose/app/
- Launch buzz: paste the X and LinkedIn/HN post URLs here
