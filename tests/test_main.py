"""Unit tests — __main__ helpers."""

from athena_diary_mcp.__main__ import build_parser, main


def test_build_parser_has_flags():
    p = build_parser()
    args = p.parse_args(["--version"])
    assert args.version is True


def test_main_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_main_describe(capsys):
    assert main(["--describe"]) == 0
    out = capsys.readouterr().out
    assert "athena_diary" in out


def test_main_health(capsys):
    assert main(["health"]) == 0
    assert '"status": "ok"' in capsys.readouterr().out


def test_main_no_args_prints_help(capsys):
    assert main([]) == 1
    assert capsys.readouterr().out
