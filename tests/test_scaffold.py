"""Unit tests — version / describe / health."""

from athena_diary_mcp import __version__
from athena_diary_mcp.describe import DESCRIBE_SPEC, describe
from athena_diary_mcp.health import health
from athena_diary_mcp.version import __version__ as version_mod


def test_version_string():
    assert __version__ == "0.1.0"
    assert version_mod == __version__


def test_describe_contract():
    spec = describe()
    assert spec["contract_version"] == "1.0"
    assert spec["plugin"]["name"] == "athena_diary"
    assert spec["plugin"]["version"] == __version__
    assert any(c["name"] == "health" for c in spec["commands"])
    # deepcopy — mutating return must not touch module constant
    spec["plugin"]["name"] = "mutated"
    assert DESCRIBE_SPEC["plugin"]["name"] == "athena_diary"


def test_health_payload():
    h = health()
    assert h["status"] == "ok"
    assert h["plugin"] == "athena_diary"
    assert h["version"] == __version__
    assert h["stage"] == "scaffold"
