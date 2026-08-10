"""E2E — CLI entrypoints for scaffold smoke."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "athena_diary_mcp", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_version():
    r = _run("--version")
    assert r.returncode == 0
    assert r.stdout.strip() == "0.1.0"


def test_cli_describe():
    r = _run("--describe")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["plugin"]["name"] == "athena_diary"
    assert data["contract_version"] == "1.0"


def test_cli_health():
    r = _run("health")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["status"] == "ok"
    assert data["stage"] == "mcp"
    assert any(c["name"] == "diary_search" for c in json.loads(_run("--describe").stdout)["commands"])


def test_cli_help_exit_nonzero_without_command():
    r = _run()
    assert r.returncode == 1
    assert "Athena Diary" in r.stdout or "usage" in r.stdout.lower()
