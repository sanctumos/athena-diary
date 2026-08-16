"""MCP dispatch + server surface tests (#2432)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from athena_diary_mcp.__main__ import _env_port, main
from athena_diary_mcp.server import (
    TOOLS_META,
    create_server,
    dispatch_tool,
    register_tools_core,
)


def test_tools_meta_names():
    names = {t["name"] for t in TOOLS_META}
    assert names == {
        "diary_write",
        "diary_get",
        "diary_search",
        "diary_sleeptime_pass",
    }


def test_dispatch_write_get_search_sleeptime(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "mcp.db"))
    monkeypatch.setenv("DIARY_EMBED_MODE", "hash")
    out = dispatch_tool(
        "diary_write",
        {"body": "MCP write path about Venice ops", "summary": "venice ops"},
    )
    entry = json.loads(out)
    assert entry["id"] > 0
    assert entry["body"].startswith("MCP write")

    got = json.loads(dispatch_tool("diary_get", {"entry_id": entry["id"]}))
    assert got["id"] == entry["id"]
    assert "see_also_entry_ids" in got
    assert "lesson_family_slug" in got
    assert "tags" in got

    hits = json.loads(dispatch_tool("diary_search", {"query": "Venice", "limit": 5}))
    assert any(h["id"] == entry["id"] for h in hits)

    dispatch_tool("diary_write", {"body": "second backlog entry for sleeptime clerk"})
    result = json.loads(dispatch_tool("diary_sleeptime_pass", {"limit": 5}))
    assert result["processed"] >= 1


def test_dispatch_unknown_and_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "mcp.db"))
    assert "Unknown tool" in dispatch_tool("nope", {})
    assert "Error:" in dispatch_tool("diary_write", {"body": "  "})
    assert "Error:" in dispatch_tool("diary_get", {"entry_id": 99999})


def test_dispatch_unexpected_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("athena_diary_mcp.server.connect", boom)
    assert "Error: boom" in dispatch_tool("diary_search", {"query": "x"})


def test_create_server_requires_mcp():
    try:
        import mcp  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError, match="mcp package"):
            create_server()
    else:
        srv = create_server()
        assert srv is not None


@pytest.mark.asyncio
async def test_register_tools_core():
    listed = {}
    called = {}

    def list_deco(fn):
        listed["fn"] = fn
        return fn

    def call_deco(fn):
        called["fn"] = fn
        return fn

    def text_factory(**kwargs):
        return kwargs

    def tool_factory(**kwargs):
        return kwargs

    tools = register_tools_core(list_deco, call_deco, text_factory, tool_factory)
    assert len(tools) == 4
    out = await listed["fn"]()
    assert len(out) == 4
    # call_tool path
    with patch(
        "athena_diary_mcp.server.dispatch_tool", return_value='{"ok":true}'
    ):
        texts = await called["fn"]("diary_write", {"body": "x"})
    assert texts[0]["text"] == '{"ok":true}'


def test_env_port(monkeypatch):
    monkeypatch.setenv("MCP_PORT", "9001")
    assert _env_port("MCP_PORT", 8000) == 9001
    monkeypatch.setenv("MCP_PORT", "nope")
    assert _env_port("MCP_PORT", 8000) == 8000


def test_main_serve_stdio_mocked(monkeypatch):
    ran = {"n": 0}

    async def fake_stdio():
        ran["n"] += 1

    monkeypatch.setattr("athena_diary_mcp.__main__._run_stdio", fake_stdio)
    assert main(["serve"]) == 0
    assert ran["n"] == 1


def test_main_serve_sse_mocked(monkeypatch):
    ran = {"n": 0}

    async def fake_sse(args):
        ran["n"] += 1
        assert args.sse is True

    monkeypatch.setattr("athena_diary_mcp.__main__._run_sse", fake_sse)
    assert main(["serve", "--sse"]) == 0
    assert ran["n"] == 1


def test_main_serve_import_error(monkeypatch):
    async def boom():
        raise ImportError("missing mcp")

    monkeypatch.setattr("athena_diary_mcp.__main__._run_stdio", boom)
    assert main(["serve"]) == 2


def test_main_serve_keyboard_interrupt(monkeypatch):
    async def boom():
        raise KeyboardInterrupt()

    monkeypatch.setattr("athena_diary_mcp.__main__._run_stdio", boom)
    assert main(["serve"]) == 0
