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


def tmp_csv(header, rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=header); w.writeheader(); w.writerows(rows); f.close()
    return f.name


class Creators(unittest.TestCase):
    def test_tiers_and_low_effort(self):
        self.assertEqual([tier(x) for x in (5_000, 10_000, 99_999, 100_000, 500_000, 1_000_000)], ["nano", "micro", "micro", "mid", "macro", "mega"])
        self.assertEqual(low_effort_ratio(["great video", "great video!", "🔥🔥", "nice one", "wow thanks"]), 2 / 5)
        self.assertIsNone(low_effort_ratio(["a", "b"]))

    def test_demo_flags_suspicious_and_does_not_flag_normals(self):
        c = connect(); seed_all(c)
        sc = {s["handle"]: s for s in score_creators(c)}
        for h in ("creator_05", "creator_17"):
            self.assertEqual(sc[h]["risk"]["label"], "high"); self.assertLess(sc[h]["score"], 40)
        self.assertEqual(sum(s["risk"]["label"] == "high" for s in sc.values()), 2)      # no false positives on normals
        self.assertEqual(sum(s["risk"]["label"] == "medium" for s in sc.values()), 0)
        self.assertIn("not proof", sc["creator_05"]["risk"]["disclaimer"])

    def test_small_cohort_withholds_score(self):
        c = connect()
        for i in range(3):
            cid = insert_id(c, "INSERT INTO creators (handle, platform, category, followers, rate_usd) VALUES (?,?,?,?,?)", (f"h{i}", "tiktok", "film", 50_000, 500))
            for p in range(8):
                c.execute("INSERT INTO creator_posts (creator_id, posted_at, views, likes, comments, shares) VALUES (?,?,?,?,?,?)", (cid, f"2026-01-{p + 1:02d}T00:00:00Z", 20_000, 900, 90, 20))
        r = score_creators(c)
        self.assertTrue(all(x["score"] is None and "withheld" in x["note"] for x in r))
        self.assertAlmostEqual(r[0]["cost"]["cpm_usd"], 500 / 20)                         # $500 / 20k views

    def test_category_fit_orders_first_and_csv_stores_ratio_not_text(self):
        c = connect(); seed_all(c)
        r = score_creators(c, categories=("film",))
        fits = [x["fit"] for x in r]; self.assertEqual(fits, sorted(fits, reverse=True))
        self.assertTrue(all(x["category"] == "film" for x in r if x["fit"]))
        d = connect()
        p = tmp_csv(["handle", "platform", "followers", "post_date", "views", "likes", "comments", "sample_comments"],
                    [dict(handle="@Z", platform="TikTok", followers="1000", post_date="2026-01-01", views="500", likes="50", comments="5", sample_comments="nice|nice|🔥|great one|wow ok")])
        res = import_creator_posts(d, p); os.unlink(p)
        self.assertEqual(res["accepted"], 1)
        row = d.execute("SELECT dup_comment_ratio FROM creator_posts").fetchone()
        self.assertAlmostEqual(row["dup_comment_ratio"], 2 / 5)
        self.assertEqual(d.execute("SELECT handle FROM creators").fetchone()["handle"], "z")      # normalised
        q = tmp_csv(["handle", "platform", "captured_at", "followers"], [dict(handle="z", platform="tiktok", captured_at="2026-01-01", followers="1000"), dict(handle="nobody", platform="tiktok", captured_at="2026-01-01", followers="5")])
        res = import_followers(d, q); os.unlink(q)
        self.assertEqual((res["accepted"], len(res["rejected"])), (1, 1))


if __name__ == "__main__":
    unittest.main()
