# SPDX-License-Identifier: AGPL-3.0-only
"""SMCP / agent-facing describe contract."""

from __future__ import annotations

import copy
from typing import Any, Dict

from .server import TOOLS_META
from .version import __version__

DESCRIBE_SPEC: Dict[str, Any] = {
    "contract_version": "1.0",
    "plugin": {
        "name": "athena_diary",
        "version": __version__,
        "description": (
            "Athena Diary — off-context SQLite journal with MCP tools "
            "(write/get/search/sleeptime clerk). Named after Sanctum agent Athena "
            "(user #1 of this pattern); not Athena-exclusive — any agent can run an instance."
        ),
    },
    "commands": [
        {
            "name": "health",
            "description": "Return plugin health and version.",
            "parameters": [],
        },
    ],
}


def describe() -> Dict[str, Any]:
    """Return SMCP describe JSON including diary tools (deepcopy-safe)."""
    spec = copy.deepcopy(DESCRIBE_SPEC)
    spec["plugin"]["version"] = __version__
    for t in TOOLS_META:
        props = t["inputSchema"].get("properties") or {}
        required = set(t["inputSchema"].get("required") or [])
        params = []
        for pname, pschema in props.items():
            params.append(
                {
                    "name": pname,
                    "type": pschema.get("type", "string"),
                    "required": pname in required,
                    "description": pschema.get("description", ""),
                }
            )
        spec["commands"].append(
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": params,
            }
        )
    return spec
