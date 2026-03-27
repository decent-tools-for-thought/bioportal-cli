from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bioportal_cli.client import BioPortalClient
from bioportal_cli.docs import ENDPOINT_SPECS, UPSTREAM_DOCS_URL, WORKFLOW_SPECS

OutputMode = str


@dataclass(frozen=True)
class CommandResult:
    payload: Any
    is_binary: bool = False


def parse_kv_pairs(values: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"invalid key=value entry: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if key == "":
            raise ValueError(f"invalid key=value entry: {item}")
        parsed[key] = value
    return parsed


def bool_or_none(value: bool | None) -> bool | None:
    return value


def common_params(args: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name in [
        "include",
        "format",
        "page",
        "pagesize",
        "include_views",
        "display_context",
        "display_links",
        "download_format",
    ]:
        if hasattr(args, name):
            val = getattr(args, name)
            if val is not None:
                params[name] = val
    return params


def endpoint_catalog() -> list[dict[str, str]]:
    return [
        {"family": spec.family, "method": spec.method, "path": spec.path, "summary": spec.summary}
        for spec in ENDPOINT_SPECS
    ]


def endpoint_families() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for spec in ENDPOINT_SPECS:
        grouped.setdefault(spec.family, []).append(
            {"method": spec.method, "path": spec.path, "summary": spec.summary}
        )
    return grouped


def docs_info() -> dict[str, Any]:
    return {
        "upstream_docs": UPSTREAM_DOCS_URL,
        "endpoint_count": len(ENDPOINT_SPECS),
        "workflow_count": len(WORKFLOW_SPECS),
        "families": sorted({spec.family for spec in ENDPOINT_SPECS}),
    }


def execute_generic(
    client: BioPortalClient,
    *,
    method: str,
    path: str,
    query_pairs: list[str] | None,
    body_json: str | None,
    raw: bool,
    binary: bool,
) -> CommandResult:
    params = parse_kv_pairs(query_pairs)
    parsed_json: Any | None = None
    if body_json is not None:
        parsed_json = json.loads(body_json)

    if binary:
        content = client.request_bytes(method, path, params=params)
        return CommandResult(payload=content, is_binary=True)
    if raw:
        text = client.request_raw(method, path, params=params)
        return CommandResult(payload=text)
    envelope = client.request(method, path, params=params, json_body=parsed_json)
    return CommandResult(payload=envelope.data)


def render_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        return f"<binary payload: {len(payload)} bytes>"
    if isinstance(payload, list):
        if not payload:
            return "[]"
        lines: list[str] = []
        for idx, item in enumerate(payload, start=1):
            if isinstance(item, dict):
                ident = item.get("@id") or item.get("id") or item.get("acronym") or item.get("name")
                label = item.get("prefLabel") or item.get("label") or item.get("name")
                if ident is None and label is None:
                    lines.append(f"{idx}. {json.dumps(item, ensure_ascii=True)}")
                elif label is None:
                    lines.append(f"{idx}. {ident}")
                else:
                    lines.append(f"{idx}. {label} ({ident})")
            else:
                lines.append(f"{idx}. {item}")
        return "\n".join(lines)
    if isinstance(payload, dict):
        preferred_order = ["@id", "id", "acronym", "name", "prefLabel", "description"]
        lines = []
        seen = set()
        for key in preferred_order:
            if key in payload:
                lines.append(f"{key}: {payload[key]}")
                seen.add(key)
        for key in sorted(payload.keys()):
            if key in seen:
                continue
            value = payload[key]
            if isinstance(value, (dict, list)):
                continue
            lines.append(f"{key}: {value}")
        if not lines:
            return json.dumps(payload, indent=2, ensure_ascii=True)
        return "\n".join(lines)
    return str(payload)


def format_output(payload: Any, *, output: OutputMode) -> str:
    if output == "json":
        return json.dumps(payload, indent=2, ensure_ascii=True)
    if output == "jsonl":
        if isinstance(payload, list):
            return "\n".join(json.dumps(item, ensure_ascii=True) for item in payload)
        return json.dumps(payload, ensure_ascii=True)
    if output == "text":
        return render_text(payload)
    raise ValueError(f"unknown output format: {output}")


def write_binary_output(payload: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
