# SPDX-License-Identifier: AGPL-3.0-only
"""Athena Diary MCP server — diary_write/get/search/sleeptime_pass."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Callable, List, Optional

from .db import connect
from .search import search_diary
from .sleeptime import sleeptime_pass
from .store import DiaryError, entry_detail, get_entry, write_entry
from .version import __version__

logger = logging.getLogger(__name__)

_SEE_ALSO_HELP = (
    "Cross-reference links live in see_also. Sleeptime links semantically related entries "
    "(same thread, recurring pattern, a later note revisiting an earlier one). Each link is "
    "stored both ways: when a newer entry is linked to an older one, diary_get on the older "
    "entry lists the newer id in see_also_newer_entry_ids (and the newer entry lists the older "
    "in see_also_older_entry_ids). Original entries stay canonical—write corrections as new "
    "entries. lesson_family_slug groups thematic siblings."
)

TOOLS_META = [
    {
        "name": "diary_write",
        "description": (
            "Append a diary entry (body required). Do not edit old entries in place—when a view "
            "changes, write a new entry and cite the earlier entry id in the body if useful; "
            "sleeptime may link them via see_also. Optional summary, sensitivity_note, source, "
            "run_id, message_id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "body": {
                    "type": "string",
                    "description": "Full diary text. Non-empty. New entries only—no in-place edits.",
                },
                "summary": {
                    "type": "string",
                    "description": "Optional hot-path gist; sleeptime may rewrite.",
                },
                "sensitivity_note": {"type": "string"},
                "source": {"type": "string", "default": "hot_turn"},
                "run_id": {"type": "string"},
                "message_id": {"type": "string"},
            },
            "required": ["body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "diary_get",
        "description": (
            "Fetch one diary entry by id (full body). Response includes see_also_entry_ids "
            "(all related entries), see_also_older_entry_ids, see_also_newer_entry_ids "
            "(bidirectional crosslinks by age), lesson_family_slug, and tags. "
            + _SEE_ALSO_HELP
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "integer",
                    "description": "Entry primary key from diary_write or diary_search.",
                }
            },
            "required": ["entry_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "diary_search",
        "description": (
            "Search diary by keyword/semantic over summaries. Returns ids + summaries + dates "
            "(not full bodies). Use diary_get on a hit to read the body and see_also_entry_ids "
            "for related entries on the same thread."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "diary_sleeptime_pass",
        "description": (
            "Clerk: process up to N unprocessed entries—template summary, tags, lesson_family, "
            "re-embed, and see_also cross-refs when summaries are semantically related (same "
            "thread / recurring pattern / revisiting an earlier entry). Idempotent. "
            + _SEE_ALSO_HELP
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Max unprocessed entries to clerk this pass.",
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def dispatch_tool(name: str, arguments: dict) -> str:
    """Pure tool dispatch (no MCP dependency) — used by server and unit tests."""
    args = arguments or {}
    try:
        if name == "diary_write":
            conn = connect()
            try:
                e = write_entry(
                    conn,
                    args.get("body") or "",
                    summary=args.get("summary"),
                    sensitivity_note=args.get("sensitivity_note"),
                    source=args.get("source") or "hot_turn",
                    run_id=args.get("run_id"),
                    message_id=args.get("message_id"),
                )
                return _json(asdict(e))
            finally:
                conn.close()
        if name == "diary_get":
            conn = connect()
            try:
                e = get_entry(conn, int(args["entry_id"]))
                return _json(entry_detail(conn, e))
            finally:
                conn.close()
        if name == "diary_search":
            conn = connect()
            try:
                limit = int(args.get("limit") or 20)
                hits = search_diary(conn, args.get("query") or "", limit=limit)
                return _json([asdict(h) for h in hits])
            finally:
                conn.close()
        if name == "diary_sleeptime_pass":
            conn = connect()
            try:
                limit = int(args.get("limit") or 10)
                result = sleeptime_pass(conn, limit=limit)
                return _json(asdict(result))
            finally:
                conn.close()
        return f"Unknown tool: {name}"
    except DiaryError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error("tool %s failed: %s", name, e, exc_info=True)
        return f"Error: {e}"


def create_server():
    """Create MCP Server instance. Requires optional dep: pip install 'athena-diary[mcp]'."""
    try:
        from mcp.server import Server
    except ImportError as e:
        raise ImportError(
            "mcp package required for server mode. Install: pip install 'athena-diary[mcp]'"
        ) from e
    return Server(name="athena-diary-mcp", version=__version__)


def register_tools(server) -> None:
    """Register tools on an mcp.server.Server (mcp 1.x decorator API)."""
    from mcp.types import TextContent, Tool

    tools = [
        Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
        for t in TOOLS_META
    ]

    @server.list_tools()
    async def list_tools():
        return tools

    @server.call_tool()
    async def call_tool(tool_name: str, arguments: dict):
        text = dispatch_tool(tool_name, arguments or {})
        return [TextContent(type="text", text=text)]


def register_tools_core(
    list_tools_decorator,
    call_tool_decorator,
    text_content_factory,
    tool_factory,
) -> list:
    """
    Testable registration core (inject MCP decorators/factories).

    Mirrors mcp 1.x ``@server.list_tools()`` / ``@server.call_tool()`` wiring.
    """
    tools = [
        tool_factory(
            name=t["name"], description=t["description"], inputSchema=t["inputSchema"]
        )
        for t in TOOLS_META
    ]

    @list_tools_decorator
    async def list_tools():
        return tools

    @call_tool_decorator
    async def call_tool(tool_name: str, arguments: dict):
        text = dispatch_tool(tool_name, arguments or {})
        return [text_content_factory(type="text", text=text)]

    return tools
