# SPDX-License-Identifier: AGPL-3.0-only
"""CLI entry — scaffold supports --version, --describe, health. Full MCP in later slice."""

from __future__ import annotations

import argparse
import json
import sys

from .describe import describe
from .health import health
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Athena Diary MCP (SanctumOS) — scaffold CLI",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print package version and exit",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Print SMCP describe JSON and exit",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("health", help="Print health JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.describe:
        print(json.dumps(describe(), indent=2))
        return 0

    if args.command == "health":
        print(json.dumps(health(), indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
