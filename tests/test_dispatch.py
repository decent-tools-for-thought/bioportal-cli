from __future__ import annotations

import argparse

from bioportal_cli.cli import build_parser
from bioportal_cli.config import Config


def _cfg() -> Config:
    return Config(api_key="k", base_url="https://data.bioontology.org", timeout=30.0)


def test_docs_catalog_runs() -> None:
    parser = build_parser()
    args = parser.parse_args(["docs", "catalog"])
    from bioportal_cli.cli import dispatch

    out = dispatch(args, _cfg())
    assert isinstance(out.payload, list)
    assert any(item["path"] == "/search" for item in out.payload)


def test_parser_for_major_families() -> None:
    parser = build_parser()
    ns: argparse.Namespace = parser.parse_args(["search", "--q", "melanoma"])
    assert ns.command == "search"
    ns = parser.parse_args(["ontologies", "get", "NCIT"])
    assert ns.command == "ontologies"
    ns = parser.parse_args(["users", "authenticate", "--data-json", "{}"])
    assert ns.command == "users"
    ns = parser.parse_args(["workflows", "concept-resolve", "NCIT", "melanoma"])
    assert ns.command == "workflows"


def test_invalid_json_body_error(capsys: object) -> None:
    from bioportal_cli.cli import main

    rc = main(["users", "authenticate", "--data-json", "{"])
    assert rc == 2
    err = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "error:" in err


def test_workflow_scope_validation(capsys: object) -> None:
    from bioportal_cli.cli import main

    rc = main(["workflows", "notes-thread-export", "--class-id", "X"])
    assert rc == 2
    err = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "requires --ontology" in err
