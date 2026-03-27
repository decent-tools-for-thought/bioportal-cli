from __future__ import annotations

from bioportal_cli.cli import main


def test_bare_invocation_prints_help(capsys: object) -> None:
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "usage: bioportal" in out


def test_top_level_help_works(capsys: object) -> None:
    rc = main(["--help"])
    assert rc == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "search" in out
    assert "ontologies" in out


def test_subcommand_help_works(capsys: object) -> None:
    rc = main(["ontologies", "--help"])
    assert rc == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "latest-submission" in out
