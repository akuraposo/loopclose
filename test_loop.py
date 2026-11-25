#!/usr/bin/env python3
"""Unit and headless browser end-to-end tests for LoopClose."""
from __future__ import annotations

import tempfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

import loop

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class LoopCloseUnitTests(unittest.TestCase):
    def test_parse_run_end_on_committed_kane_proofs(self):
        bug_path = loop.PROOF / "01-bug-confirmed.ndjson"
        fix_path = loop.PROOF / "02-fix-verified.ndjson"
        open_path = loop.PROOF / "03-deploy-unlocked.ndjson"
        self.assertTrue(bug_path.exists())
        self.assertTrue(fix_path.exists())
        self.assertTrue(open_path.exists())

        bug_end = loop.parse_run_end(bug_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(bug_end)
        self.assertEqual(bug_end["status"], "passed")
        self.assertEqual(bug_end["final_state"]["gate_text"], "GATE: OPEN — deploy allowed")
        self.assertIn("test-manager.lambdatest.com", bug_end["test_url"])

        fix_end = loop.parse_run_end(fix_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(fix_end)
        self.assertEqual(fix_end["status"], "passed")
        self.assertEqual(fix_end["final_state"]["gate_text"], "GATE: CLOSED")
        self.assertIn("test-manager.lambdatest.com", fix_end["test_url"])

        open_end = loop.parse_run_end(open_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(open_end)
        self.assertEqual(open_end["status"], "passed")
        self.assertEqual(open_end["final_state"]["release_gate_text"], "GATE: OPEN — deploy allowed")
        self.assertIn("test-manager.lambdatest.com", open_end["test_url"])

    def test_parse_run_end_ignores_malformed_lines(self):
        sample = "noise line\n{bad json\n{\"type\":\"step\"}\n{\"type\":\"run_end\",\"status\":\"passed\",\"credits_consumed\":1.5}\n"
        res = loop.parse_run_end(sample)
        self.assertEqual(res["status"], "passed")
        self.assertEqual(res["credits_consumed"], 1.5)

    def test_set_variant_writes_expected_flag(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.js"
            loop.set_variant(True, config_path=cfg)
            self.assertIn("window.LOOPCLOSE_BUG = true;", cfg.read_text(encoding="utf-8"))
            loop.set_variant(False, config_path=cfg)
            self.assertIn("window.LOOPCLOSE_BUG = false;", cfg.read_text(encoding="utf-8"))

    def test_local_app_server_serves_assets(self):
        with loop.LocalAppServer(loop.APP, port=0) as srv:
            with urllib.request.urlopen(f"{srv.base_url}/index.html") as r:
                self.assertEqual(r.status, 200)
                html = r.read().decode("utf-8")
                self.assertIn("LoopClose", html)
            with urllib.request.urlopen(f"{srv.base_url}/config.js") as r:
                self.assertEqual(r.status, 200)
                self.assertIn("LOOPCLOSE_BUG", r.read().decode("utf-8"))


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class LoopCloseBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._srv = loop.LocalAppServer(loop.APP, port=0)
        cls._srv.__enter__()
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()
        cls._srv.__exit__(None, None, None)

    def setUp(self):
        loop.set_variant(False)

    def tearDown(self):
        loop.set_variant(False)

    def test_initial_gate_closed_and_deploy_blocked(self):
        page = self._browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self._srv.base_url}/")
        self.assertEqual(page.text_content("#gate"), "GATE: CLOSED")
        page.click("#deploy")
        self.assertIn("BLOCKED", page.text_content("#agent"))
        self.assertEqual(errors, [])
        page.close()

    def test_regression_vs_fix_query_behavior_matches_kane_runs(self):
        page = self._browser.new_page()
        url = f"{self._srv.base_url}/?verdict=failed&evidence=https%3A%2F%2Fexample.com%2Fproof"

        loop.set_variant(True)
        page.goto(url)
        self.assertEqual(page.text_content("#gate"), "GATE: OPEN — deploy allowed")
        self.assertIn("state-bug", page.get_attribute("body", "class") or "")

        loop.set_variant(False)
        page.goto(url)
        self.assertEqual(page.text_content("#gate"), "GATE: CLOSED")
        self.assertIn("state-fixed", page.get_attribute("body", "class") or "")
        page.close()

    def test_untrusted_evidence_host_is_rejected_on_fixed_build(self):
        page = self._browser.new_page()
        page.goto(f"{self._srv.base_url}/?verdict=passed&evidence=https%3A%2F%2Fevil.example%2Ffake")
        self.assertEqual(page.text_content("#gate"), "GATE: CLOSED")
        self.assertIn("untrusted", (page.text_content("#evidence") or "").lower())
        page.close()

    def test_interactive_checkout_and_trusted_proof_unlocks_gate(self):
        page = self._browser.new_page()
        page.goto(f"{self._srv.base_url}/")

        # Broken variant leaves WELCOME10 total wrong ($100.00) and blocks proof
        page.select_option("#variant", "broken")
        page.click("#run-flow")
        self.assertEqual(page.text_content("#flow-total"), "$100.00")
        self.assertEqual(page.text_content("#sandbox-badge"), "FLOW FAILED")
        self.assertEqual(page.text_content("#gate"), "GATE: CLOSED")

        page.click("#use-sample-proof")
        page.click("#prove")
        self.assertIn("broken", (page.text_content("#link-error") or "").lower())
        self.assertEqual(page.text_content("#gate"), "GATE: CLOSED")

        # Switch to good variant -> badge resets to IDLE, then WELCOME10 applies ($90.00) -> apply real Test Manager proof -> SHIPPED
        page.select_option("#variant", "good")
        self.assertEqual(page.text_content("#sandbox-badge"), "IDLE")
        page.click("#run-flow")
        self.assertEqual(page.text_content("#flow-total"), "$90.00")
        self.assertEqual(page.text_content("#sandbox-badge"), "FLOW PASSED")

        page.click("#use-sample-proof")
        page.click("#prove")
        page.wait_for_load_state("load")
        self.assertEqual(page.text_content("#gate"), "GATE: OPEN — deploy allowed")
        self.assertIn("state-proof", page.get_attribute("body", "class") or "")
        page.click("#deploy")
        self.assertIn("SHIPPED", page.text_content("#agent"))
        page.close()

    def test_interactive_signup_flow_and_xss_safety(self):
        page = self._browser.new_page()
        dialogs = []
        page.on("dialog", lambda d: dialogs.append(d.message))
        page.goto(f"{self._srv.base_url}/")
        page.select_option("#flow", "signup")
        page.fill("#signup-email", "<img src=x onerror=alert(1)>@example.com")
        page.click("#run-signup")
        self.assertEqual(page.text_content("#sandbox-badge"), "FLOW FAILED")

        page.fill("#signup-email", "judge@testmuai.com")
        page.click("#run-signup")
        self.assertEqual(page.text_content("#sandbox-badge"), "FLOW PASSED")
        self.assertIn("judge@testmuai.com", page.text_content("#flow-status") or "")
        self.assertEqual(dialogs, [])
        page.close()


if __name__ == "__main__":
    unittest.main()
