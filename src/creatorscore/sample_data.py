"""SYNTHETIC creators (is_sample=1); two are built to look suspicious."""
import math
import random
from datetime import datetime, timedelta, timezone

from .db import insert_id, iso


def seed_creators(conn, seed_value=5, n=24):
    """SYNTHETIC creators; two are built to look suspicious (follower jump, duplicate comments, weak reach)."""
    rng = random.Random(seed_value)
    plats, cats, bad = ("tiktok", "instagram", "youtube"), ("film", "gaming", "comedy", "lifestyle"), {5, 17}
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for i in range(n):
        followers = int(math.exp(rng.uniform(math.log(8e3), math.log(2.5e6))))
        cid = insert_id(conn, "INSERT INTO creators (handle, platform, category, followers, rate_usd, is_sample) VALUES (?,?,?,?,?,1)",
                        (f"creator_{i:02d}", plats[i % 3], cats[i % 4], followers, round(followers * rng.uniform(0.008, 0.02), 2)))
        ratio, er = (0.01, 0.004) if i in bad else (rng.uniform(0.08, 0.35), rng.uniform(0.03, 0.09))
        for p in range(12):
            v = max(1, int(followers * ratio * math.exp(rng.gauss(0, 0.4))))
            dup = (0.5 + rng.uniform(0, 0.1)) if i in bad else (rng.uniform(0.0, 0.08) if p % 3 == 0 else None)
            conn.execute("INSERT INTO creator_posts (creator_id, posted_at, views, likes, comments, shares, dup_comment_ratio) VALUES (?,?,?,?,?,?,?)",
                         (cid, iso(start + timedelta(days=p * 3)), v, int(v * er * 0.85), int(v * er * 0.1), int(v * er * 0.05), dup))
        f = followers * 0.8
        for d in range(30):
            f *= 1 + rng.uniform(0.0, 0.004) + (0.45 if (i in bad and d == 20) else 0)
            conn.execute("INSERT INTO creator_followers (creator_id, captured_at, followers) VALUES (?,?,?)",
                         (cid, iso(start + timedelta(days=d)), int(f)))
    conn.commit()


def seed_all(conn):
    seed_creators(conn)
