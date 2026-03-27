from __future__ import annotations

import json

from bioportal_cli.core import format_output


def test_format_jsonl_list() -> None:
    payload = [{"a": 1}, {"b": 2}]
    out = format_output(payload, output="jsonl")
    lines = out.splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["a"] == 1


def test_format_text_dict() -> None:
    out = format_output({"acronym": "NCIT", "name": "NCI Thesaurus"}, output="text")
    assert "acronym:" in out
