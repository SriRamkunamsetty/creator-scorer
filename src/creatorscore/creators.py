"""Project 4: Creator quality scorer. Explainable, cohort-relative scoring of creators from public metrics.

HONEST SCOPE: authenticity "risk" is a set of heuristic signals from public numbers, NOT proof of fraud.
Benchmarks are computed from YOUR imported cohort (no invented industry constants); with fewer than 5
comparable creators the score is withheld rather than faked. Cohort-relative percentiles mean scores are
only comparable inside one cohort."""
import csv
import re
from statistics import median

from .db import iso, parse_ts
from .stats import pct_rank, robust_z

TIERS = ((1_000_000, "mega"), (500_000, "macro"), (100_000, "mid"), (10_000, "micro"), (0, "nano"))
W = {"follower_spike": 0.35, "low_reach": 0.20, "low_engagement": 0.15, "duplicate_comments": 0.30}


def tier(followers):
    return next(name for lim, name in TIERS if followers >= lim)


def low_effort_ratio(comments, min_n=5):
    """Share of sampled comments that are exact duplicates or contain no words (emoji/one-char spam)."""
    if len(comments) < min_n:
        return None
    seen, flagged = set(), 0
    for c in comments:
        norm = re.sub(r"[^\w\s]", "", c.lower()).strip()
        if not re.search(r"[a-z]{2,}", norm) or norm in seen:
            flagged += 1
        seen.add(norm)
    return flagged / len(comments)


def import_creator_posts(conn, path):
    """Columns: handle, platform, followers, post_date, views, likes, comments
    [, category, rate_usd, shares, sample_comments ('|'-separated; only a ratio is stored, never the text)]."""
    ok, rejected = 0, []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        miss = [c for c in ("handle", "platform", "followers", "post_date", "views", "likes", "comments") if c not in (rd.fieldnames or [])]
        if miss:
            raise ValueError(f"CSV is missing required columns: {miss}")
        for n, r in enumerate(rd, start=2):
            try:
                nums = {k: int(float(r.get(k) or 0)) for k in ("followers", "views", "likes", "comments", "shares")}
                if min(nums.values()) < 0 or nums["followers"] == 0:
                    raise ValueError("followers must be > 0 and counters non-negative")
                rate = float(r["rate_usd"]) if r.get("rate_usd") else None
                h, p = r["handle"].strip().lstrip("@").lower(), r["platform"].strip().lower()
                conn.execute("INSERT INTO creators (handle, platform, category, followers, rate_usd) VALUES (?,?,?,?,?) "
                             "ON CONFLICT (platform, handle) DO UPDATE SET followers=excluded.followers, "
                             "category=COALESCE(excluded.category, creators.category), rate_usd=COALESCE(excluded.rate_usd, creators.rate_usd)",
                             (h, p, (r.get("category") or "").strip().lower() or None, nums["followers"], rate))
                cid = conn.execute("SELECT id FROM creators WHERE platform=? AND handle=?", (p, h)).fetchone()["id"]
                dup = low_effort_ratio([c for c in (r.get("sample_comments") or "").split("|") if c.strip()])
                conn.execute("INSERT INTO creator_posts (creator_id, posted_at, views, likes, comments, shares, dup_comment_ratio) VALUES (?,?,?,?,?,?,?) "
                             "ON CONFLICT (creator_id, posted_at) DO UPDATE SET views=excluded.views, likes=excluded.likes, "
                             "comments=excluded.comments, shares=excluded.shares, dup_comment_ratio=excluded.dup_comment_ratio",
                             (cid, iso(parse_ts(r["post_date"])), nums["views"], nums["likes"], nums["comments"], nums["shares"], dup))
                ok += 1
            except (ValueError, KeyError) as exc:
                rejected.append({"line": n, "reason": str(exc)})
    conn.commit()
    return {"accepted": ok, "rejected": rejected}


def import_followers(conn, path):
    """Columns: handle, platform, captured_at, followers. Creator must already exist."""
    ok, rejected = 0, []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for n, r in enumerate(csv.DictReader(fh), start=2):
            try:
                c = conn.execute("SELECT id FROM creators WHERE platform=? AND handle=?",
                                 (r["platform"].strip().lower(), r["handle"].strip().lstrip("@").lower())).fetchone()
                if not c:
                    raise ValueError("unknown creator (import posts first)")
                conn.execute("INSERT INTO creator_followers (creator_id, captured_at, followers) VALUES (?,?,?) "
                             "ON CONFLICT (creator_id, captured_at) DO UPDATE SET followers=excluded.followers",
                             (c["id"], iso(parse_ts(r["captured_at"])), int(float(r["followers"]))))
                ok += 1
            except (ValueError, KeyError) as exc:
                rejected.append({"line": n, "reason": str(exc)})
    conn.commit()
    return {"accepted": ok, "rejected": rejected}


def _spike(conn, cid):
    pts = [float(r["followers"]) for r in conn.execute("SELECT followers FROM creator_followers WHERE creator_id=? ORDER BY captured_at", (cid,))]
    if len(pts) < 6:
        return None
    rates = [(b - a) / a for a, b in zip(pts, pts[1:]) if a > 0]
    if len(rates) < 5:
        return None
    zs = robust_z(rates, floor=0.005)
    i = max(range(len(rates)), key=lambda k: zs[k])
    return {"flag": zs[i] >= 4 and rates[i] >= 0.05, "jump": rates[i], "z": zs[i]}


def _raw(conn, c):
    posts = conn.execute("SELECT views, likes, comments, shares, dup_comment_ratio FROM creator_posts WHERE creator_id=?", (c["id"],)).fetchall()
    views = [float(p["views"]) for p in posts if p["views"] > 0]
    if not views:
        return None
    med = median(views)
    er = [(p["likes"] + p["comments"] + p["shares"]) / p["views"] for p in posts if p["views"] > 0]
    dups = [float(p["dup_comment_ratio"]) for p in posts if p["dup_comment_ratio"] is not None]
    eng = median([p["likes"] + p["comments"] + p["shares"] for p in posts])
    return {"n_posts": len(views), "median_views": med, "er": median(er), "reach": med / c["followers"],
            "consistency": sum(0.5 * med <= v <= 2 * med for v in views) / len(views),
            "dup": sum(dups) / len(dups) if dups else None, "median_engagements": float(eng)}


def score_creators(conn, categories=(), min_posts=6, min_cohort=5):
    creators = conn.execute("SELECT id, handle, platform, category, followers, rate_usd FROM creators").fetchall()
    rows = []
    for c in creators:
        raw = _raw(conn, c)
        if raw:
            rows.append((c, raw, tier(c["followers"])))
    out = []
    for c, raw, tr in rows:
        cohort = [r for r in rows if r[0]["platform"] == c["platform"] and r[2] == tr]
        scope = f"{c['platform']} {tr}"
        if len(cohort) < min_cohort:
            cohort, scope = [r for r in rows if r[0]["platform"] == c["platform"]], f"all {c['platform']}"
        have = len(cohort) >= min_cohort
        er_pct = pct_rank([r[1]["er"] for r in cohort], raw["er"]) if have else None
        reach_pct = pct_rank([r[1]["reach"] for r in cohort], raw["reach"]) if have else None
        sp = _spike(conn, c["id"])
        sig = {}
        if sp is not None:
            sig["follower_spike"] = (sp["flag"], f"largest follower jump {sp['jump']:.0%}")
        if have:  # must be far below the cohort median, not merely the lowest of a small group
            lo_reach = reach_pct <= 10 and raw["reach"] <= median(r[1]["reach"] for r in cohort) / 3
            lo_er = er_pct <= 10 and raw["er"] <= median(r[1]["er"] for r in cohort) / 3
            sig["low_reach"] = (lo_reach, f"views/followers under a third of the {scope} median" if lo_reach else "reach in normal range")
            sig["low_engagement"] = (lo_er, f"engagement under a third of the {scope} median" if lo_er else "engagement in normal range")
        if raw["dup"] is not None:
            sig["duplicate_comments"] = (raw["dup"] >= 0.3, f"{raw['dup']:.0%} of sampled comments are duplicates or wordless")
        evaluable = sum(W[k] for k in sig)
        risk = sum(W[k] for k, (hit, _) in sig.items() if hit) / evaluable if evaluable else None
        label = "insufficient data" if evaluable < 0.5 else "high" if risk >= 0.5 else "medium" if risk >= 0.25 else "low"
        score, note = None, None
        if have:
            quality = 0.4 * er_pct + 0.3 * reach_pct + 0.3 * raw["consistency"] * 100
            score = round(quality * (1 - 0.5 * (risk or 0)), 1)
        else:
            note = f"cohort of {len(cohort)} is below {min_cohort}: score withheld, raw metrics shown"
        rate = c["rate_usd"]
        fit = (not categories) or (c["category"] in categories)
        out.append({"handle": c["handle"], "platform": c["platform"], "tier": tr, "category": c["category"], "followers": int(c["followers"]),
                    "n_posts": raw["n_posts"], "confidence": "low" if raw["n_posts"] < min_posts else "medium" if raw["n_posts"] < 12 else "high",
                    "metrics": {"median_views": raw["median_views"], "engagement_rate": raw["er"], "reach_ratio": raw["reach"], "consistency": raw["consistency"]},
                    "percentiles": {"engagement": er_pct, "reach": reach_pct, "cohort": scope},
                    "risk": {"label": label, "score": risk, "signals": [{"signal": k, "triggered": h, "detail": d} for k, (h, d) in sig.items()],
                             "disclaimer": "heuristic signals from public numbers, not proof of fraud"},
                    "cost": {"cpm_usd": rate / (raw["median_views"] / 1000) if rate else None,
                             "cpe_usd": rate / raw["median_engagements"] if rate and raw["median_engagements"] else None},
                    "score": score, "fit": fit, "note": note})
    return sorted(out, key=lambda r: (not r["fit"], r["score"] is None, -(r["score"] or 0)))
