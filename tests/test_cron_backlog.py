"""Tests for cron backlog helper (#2435 support)."""

import json

from athena_diary_mcp.cron_backlog import backlog_count, main
from athena_diary_mcp.db import connect
from athena_diary_mcp.store import write_entry


def test_backlog_and_threshold(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "c.db"))
    monkeypatch.setenv("DIARY_EMBED_MODE", "hash")
    conn = connect()
    for i in range(3):
        write_entry(conn, f"backlog item {i} for cron")
    assert backlog_count(conn) == 3
    conn.close()

    assert main(["--threshold", "10", "--dry-run"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["backlog"] == 3
    assert data["action"] == "none"

    assert main(["--threshold", "1", "--batch", "2"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["action"] == "sleeptime_pass"
    assert data["processed"] == 2
