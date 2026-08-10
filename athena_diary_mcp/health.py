# SPDX-License-Identifier: AGPL-3.0-only
"""Health / version helpers for scaffold smoke and e2e."""

from __future__ import annotations

from typing import Any, Dict

from .version import __version__


def health() -> Dict[str, Any]:
    """Return a stable health payload for CLI and future MCP tool."""
    return {
        "status": "ok",
        "plugin": "athena_diary",
        "version": __version__,
        "stage": "mcp",
    }
