# SPDX-License-Identifier: AGPL-3.0-only
"""Deploy helpers — backlog threshold check for moya cron safety net."""

from __future__ import annotations

import argparse
import json
import sys

from .db import connect
from .sleeptime import sleeptime_pass


def backlog_count(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM entries WHERE sleeptime_processed_at IS NULL"
    ).fetchone()
    return int(row["n"] if row else 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Athena diary backlog cron helper")
    p.add_argument(
        "--threshold",
        type=int,
        default=50,
        help="Invoke sleeptime_pass when unprocessed count exceeds this",
    )
    p.add_argument(
        "--batch",
        type=int,
        default=25,
        help="Max entries to process when threshold tripped",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; do not process",
    )
    args = p.parse_args(argv)
    conn = connect()
    try:
        n = backlog_count(conn)
        payload = {"backlog": n, "threshold": args.threshold, "action": "none"}
        if n > args.threshold and not args.dry_run:
            result = sleeptime_pass(conn, limit=args.batch)
            payload["action"] = "sleeptime_pass"
            payload["processed"] = result.processed
            payload["entry_ids"] = list(result.entry_ids)
        elif n > args.threshold:
            payload["action"] = "would_sleeptime_pass"
        print(json.dumps(payload))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
