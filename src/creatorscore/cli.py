"""CreatorScore command line. Run `creatorscore <command> -h` for options."""
import argparse
import json
import os

from . import __version__
from .creators import import_creator_posts, import_followers, score_creators
from .db import connect


def open_db(a):
    if getattr(a, "demo", False):
        from .sample_data import seed_all
        conn = connect(check_same_thread=False)
        seed_all(conn)
        return conn
    return connect(a.db, check_same_thread=False)


def _table(rows):
    head = f"{'#':>2}  {'creator':<14}{'platform':<10}{'tier':<7}{'score':>6}  {'risk':<18}{'data':<7}{'CPM':>8}"
    out = [head, "-" * len(head)]
    for i, r in enumerate(rows, 1):
        sc = "withheld" if r["score"] is None else f"{r['score']:.1f}"
        cpm = "n/a" if r["cost"]["cpm_usd"] is None else f"${r['cost']['cpm_usd']:.2f}"
        out.append(f"{i:>2}  @{r['handle']:<13}{r['platform']:<10}{r['tier']:<7}{sc:>6}  {r['risk']['label']:<18}{r['confidence']:<7}{cpm:>8}")
        hits = [s["detail"] for s in r["risk"]["signals"] if s["triggered"]]
        if hits:
            out.append("      ! " + "; ".join(hits))
    return "\n".join(out)


def build_parser():
    p = argparse.ArgumentParser(prog="creatorscore", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=os.environ.get("DATABASE_URL", "creatorscore.db"), help="SQLite path or postgresql:// DSN")
    common.add_argument("--demo", action="store_true", help="use in-memory SYNTHETIC demo data")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", parents=[common], help="rank creators"); s.add_argument("--categories", default="", help="comma-separated; non-matching creators sort last")
    s.add_argument("--format", choices=["table", "json"], default="table"); s.add_argument("--top", type=int, default=15)
    w = sub.add_parser("serve", parents=[common], help="read-only dashboard"); w.add_argument("--host", default="127.0.0.1"); w.add_argument("--port", type=int, default=8000)
    sub.add_parser("import-creators", parents=[common], help="handle,platform,followers,post_date,views,likes,comments[,category,rate_usd,shares,sample_comments]").add_argument("path")
    sub.add_parser("import-followers", parents=[common], help="handle,platform,captured_at,followers").add_argument("path")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        _dispatch(a)
    except (RuntimeError, ValueError, OSError) as exc:
        raise SystemExit(f"error: {exc}")


def _dispatch(a):
    if a.cmd == "score":
        rows = score_creators(open_db(a), tuple(x for x in a.categories.split(",") if x))
        print(json.dumps(rows, indent=2, default=str) if a.format == "json" else _table(rows[: a.top]))
    elif a.cmd == "serve":
        from .web import serve
        serve(open_db(a), a.host, a.port)
    elif a.cmd in ("import-creators", "import-followers"):
        fn = import_creator_posts if a.cmd == "import-creators" else import_followers
        r = fn(open_db(a), a.path); print(f"accepted={r['accepted']} rejected={len(r['rejected'])}")
        for x in r["rejected"][:20]:
            print(f"  line {x['line']}: {x['reason']}")


if __name__ == "__main__":
    main()
