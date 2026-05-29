#!/usr/bin/env python3
"""
Aggregate query_logs to produce a suggested hotlist expansion.

This is intended to run as a nightly job (cron/systemd timer) and output a JSON
file that can be reviewed/merged into the seed hotlist.

Usage:
  export VIIRS_DB_PATH="viirs_cache_local.db"
  python3 backend/query_log_aggregate.py --days 30 --limit 200 --out backend/data/top_queries.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from database import DatabaseManager


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate top queries from SQLite query_logs")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default="backend/data/top_queries.json")
    args = ap.parse_args()

    db_path = os.getenv("VIIRS_DB_PATH", "viirs_cache_local.db")
    db = DatabaseManager(db_path)
    top = db.get_top_queries(days=args.days, limit=args.limit)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "db_path": str(db_path),
        "days": args.days,
        "limit": args.limit,
        "count": len(top),
        "top_queries": top,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(top)} queries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

