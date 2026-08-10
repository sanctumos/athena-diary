# SPDX-License-Identifier: AGPL-3.0-only
"""SMCP / agent-facing describe contract (scaffold). Tools land in later Build slices."""

from __future__ import annotations

from typing import Any, Dict

from .version import __version__

DESCRIBE_SPEC: Dict[str, Any] = {
    "contract_version": "1.0",
    "plugin": {
        "name": "athena_diary",
        "version": __version__,
        "description": (
            "Athena Diary — off-context SQLite journal with MCP tools "
            "(write/search/sleeptime clerk). Scaffold only until later slices land."
        ),
    },
    "commands": [
        {
            "name": "health",
            "description": "Return plugin health and version (scaffold smoke).",
            "parameters": [],
        },
    ],
}


def describe() -> Dict[str, Any]:
    """Return a copy of the SMCP describe spec."""
    import copy

    return copy.deepcopy(DESCRIBE_SPEC)
