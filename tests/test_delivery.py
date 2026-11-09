import csv
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from creatorscore.cli import main
from creatorscore.creators import import_creator_posts, import_followers, low_effort_ratio, score_creators, tier
from creatorscore.db import connect, insert_id
from creatorscore.sample_data import seed_all
from creatorscore.web import App, make_handler



class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conn = connect(check_same_thread=False); seed_all(conn)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(App(conn)))
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def call(self, p, data=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + p, data=data)) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_api_page_and_hardening(self):
        s, h, b = self.call("/")
        self.assertEqual(s, 200); self.assertNotIn(b"innerHTML", b); self.assertIn("default-src 'none'", h["Content-Security-Policy"])
        rows = json.loads(self.call("/api/creators?categories=film")[2])
        self.assertEqual(len(rows), 24); self.assertTrue(all(r["risk"]["disclaimer"] for r in rows))
        self.assertEqual(sum(r["risk"]["label"] == "high" for r in rows), 2)
        for p in ("/api/nope", "/etc/passwd"):
            self.assertEqual(self.call(p)[0], 404)
        self.assertEqual(self.call("/api/creators", data=b"{}")[0], 405)


class Cli(unittest.TestCase):
    def test_score_table_and_json_and_imports(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["score", "--demo", "--top", "5"])
        self.assertIn("creator", buf.getvalue()); self.assertEqual(len(buf.getvalue().strip().splitlines()) >= 7, True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["score", "--demo", "--format", "json"])
        self.assertEqual(len(json.loads(buf.getvalue())), 24)
        d = tempfile.mkdtemp(); db = os.path.join(d, "t.db"); p = os.path.join(d, "p.csv")
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["handle", "platform", "followers", "post_date", "views", "likes", "comments"]); w.writerow(["a", "tiktok", "1000", "2026-01-01", "500", "50", "5"]); w.writerow(["b", "tiktok", "0", "2026-01-01", "5", "5", "5"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["import-creators", "--db", db, p])
        self.assertIn("accepted=1 rejected=1", buf.getvalue())


class Browser(unittest.TestCase):
    def test_filters_scatter_and_detail_in_a_real_browser(self):
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start(); browser = pw.chromium.launch()
        except Exception:
            self.skipTest("Playwright/Chromium not available")
        conn = connect(check_same_thread=False); seed_all(conn)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(App(conn))); threading.Thread(target=srv.serve_forever, daemon=True).start()
        errors = []
        try:
            page = browser.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{srv.server_address[1]}/"); page.wait_for_selector("tbody tr")
            self.assertEqual(page.locator("tbody tr").count(), 24); self.assertEqual(page.locator("main svg circle").count(), 24)
            page.locator("select").first.select_option("tiktok"); page.wait_for_timeout(200)
            self.assertEqual(page.locator("tbody tr").count(), 8)
            page.locator("select").first.select_option(""); page.locator("input[type=checkbox]").check(); page.wait_for_timeout(200)
            self.assertEqual(page.locator("tbody tr").count(), 22)                      # the two high-risk creators are hidden
            page.locator("input[type=checkbox]").uncheck(); page.wait_for_timeout(200)
            page.locator("tbody tr").filter(has_text="@creator_05").click(); page.wait_for_timeout(200)
            txt = page.inner_text("main")
            self.assertIn("RISK SIGNALS: HIGH", txt.upper()); self.assertIn("not proof of fraud", txt)
            for bad in ("[object", "undefined", "NaN"):
                self.assertNotIn(bad, txt)
        finally:
            browser.close(); pw.stop(); srv.shutdown(); srv.server_close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
