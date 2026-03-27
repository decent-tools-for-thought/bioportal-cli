from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from bioportal_cli.client import BioPortalClient, BioPortalError
from bioportal_cli.config import Config, ConfigError, write_config
from bioportal_cli.core import (
    CommandResult,
    common_params,
    docs_info,
    endpoint_catalog,
    endpoint_families,
    format_output,
    write_binary_output,
)


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help="BioPortal API key (or BIOPORTAL_API_KEY)")
    parser.add_argument("--base-url", help="API base URL")
    parser.add_argument("--timeout", type=float, help="HTTP timeout in seconds")
    parser.add_argument("--output", choices=["json", "jsonl", "text"], default="json")
    parser.add_argument(
        "--output-file",
        help="Write output to file instead of stdout (text/json output or binary downloads)",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Auto-follow page numbers for list endpoints returning list payloads",
    )
    parser.add_argument("--max-pages", type=int, help="Max number of pages when using --all-pages")


def _add_common_query_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--include", help="Comma-separated field include list or 'all'")
    parser.add_argument("--format", choices=["json", "jsonp", "xml"], help="Response format")
    parser.add_argument("--page", type=int, help="Result page number")
    parser.add_argument("--pagesize", type=int, help="Result page size")
    parser.add_argument("--include-views", action="store_true", default=None)
    parser.add_argument("--display-context", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--display-links", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--download-format", choices=["csv", "rdf"], help="Download conversion format"
    )


def _add_data_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-json", help="JSON request body string")
    parser.add_argument("--data-file", help="Path to JSON request body file")


def _load_json_body(args: argparse.Namespace) -> Any | None:
    data_json = getattr(args, "data_json", None)
    data_file = getattr(args, "data_file", None)
    if data_json and data_file:
        raise ValueError("use only one of --data-json or --data-file")
    if data_file:
        text = Path(data_file).read_text(encoding="utf-8")
        return json.loads(text)
    if data_json:
        return json.loads(data_json)
    return None


def _run_request(
    client: BioPortalClient,
    *,
    args: argparse.Namespace,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    binary: bool = False,
) -> CommandResult:
    merged = dict(common_params(args))
    if params:
        merged.update(params)

    if args.all_pages and method.upper() == "GET" and not binary:
        payload = client.paginate(path, params=merged, max_pages=args.max_pages)
        return CommandResult(payload=payload)

    if binary:
        data = client.request_bytes(method, path, params=merged)
        return CommandResult(payload=data, is_binary=True)

    envelope = client.request(method, path, params=merged, json_body=json_body)
    return CommandResult(payload=envelope.data)


def _enc(value: str) -> str:
    return quote(value, safe="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bioportal", description="CLI wrapper for BioPortal API")
    _add_global_flags(parser)
    sub = parser.add_subparsers(dest="command")

    p_docs = sub.add_parser("docs", help="Inspect wrapped API documentation metadata")
    docs_sub = p_docs.add_subparsers(dest="docs_cmd", required=True)
    docs_sub.add_parser("info", help="Show docs metadata")
    docs_sub.add_parser("catalog", help="List all wrapped endpoints")
    docs_sub.add_parser("families", help="Show endpoints grouped by family")

    p_config = sub.add_parser("config", help="Manage local CLI config")
    conf_sub = p_config.add_subparsers(dest="config_cmd", required=True)
    conf_sub.add_parser("show", help="Show effective config (without secret leakage)")
    p_conf_set = conf_sub.add_parser("set", help="Write config values")
    p_conf_set.add_argument("--api-key", help="API key to store")
    p_conf_set.add_argument("--base-url", help="Base URL to store")
    p_conf_set.add_argument("--timeout", type=float, help="Timeout to store")

    p_api = sub.add_parser("api", help="Generic direct API operation")
    api_sub = p_api.add_subparsers(dest="api_cmd", required=True)
    p_api_req = api_sub.add_parser("request", help="Direct request escape hatch")
    p_api_req.add_argument("method", help="HTTP method")
    p_api_req.add_argument("path", help="API path (e.g. /ontologies)")
    p_api_req.add_argument("--query", action="append", help="Query key=value (repeatable)")
    _add_data_flags(p_api_req)
    p_api_req.add_argument("--raw", action="store_true", help="Return raw response text")
    p_api_req.add_argument("--binary", action="store_true", help="Treat response as binary")

    p_search = sub.add_parser("search", help="Term search")
    _add_common_query_flags(p_search)
    p_search.add_argument("--q", required=True)
    p_search.add_argument("--ontologies")
    p_search.add_argument(
        "--require-exact-match", action=argparse.BooleanOptionalAction, default=None
    )
    p_search.add_argument("--suggest", action=argparse.BooleanOptionalAction, default=None)
    p_search.add_argument(
        "--also-search-views", action=argparse.BooleanOptionalAction, default=None
    )
    p_search.add_argument(
        "--require-definitions", action=argparse.BooleanOptionalAction, default=None
    )
    p_search.add_argument(
        "--also-search-properties", action=argparse.BooleanOptionalAction, default=None
    )
    p_search.add_argument(
        "--also-search-obsolete", action=argparse.BooleanOptionalAction, default=None
    )
    p_search.add_argument("--cui")
    p_search.add_argument("--semantic-types")
    p_search.add_argument("--language")
    p_search.add_argument("--ontology", help="Ontology ID for subtree searches")
    p_search.add_argument("--subtree-root-id", help="URI-encoded class ID for subtree searches")
    p_search.add_argument("--roots-only", action=argparse.BooleanOptionalAction, default=None)

    p_prop_search = sub.add_parser("property-search", help="Ontology property search")
    _add_common_query_flags(p_prop_search)
    p_prop_search.add_argument("--q", required=True)
    p_prop_search.add_argument("--ontologies")
    p_prop_search.add_argument(
        "--require-exact-match", action=argparse.BooleanOptionalAction, default=None
    )
    p_prop_search.add_argument(
        "--also-search-views", action=argparse.BooleanOptionalAction, default=None
    )
    p_prop_search.add_argument(
        "--require-definitions", action=argparse.BooleanOptionalAction, default=None
    )
    p_prop_search.add_argument("--ontology-types")
    p_prop_search.add_argument("--property-types")

    p_annotator = sub.add_parser("annotator", help="Annotate text")
    _add_common_query_flags(p_annotator)
    p_annotator.add_argument("--text", required=True)
    p_annotator.add_argument("--ontologies")
    p_annotator.add_argument("--semantic-types")
    p_annotator.add_argument(
        "--expand-semantic-types-hierarchy", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument(
        "--expand-class-hierarchy", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument("--class-hierarchy-max-level", type=int)
    p_annotator.add_argument(
        "--expand-mappings", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument("--stop-words")
    p_annotator.add_argument("--minimum-match-length", type=int)
    p_annotator.add_argument(
        "--exclude-numbers", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument(
        "--whole-word-only", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument(
        "--exclude-synonyms", action=argparse.BooleanOptionalAction, default=None
    )
    p_annotator.add_argument("--longest-only", action=argparse.BooleanOptionalAction, default=None)

    p_recommender = sub.add_parser("recommender", help="Recommend ontologies")
    _add_common_query_flags(p_recommender)
    p_recommender.add_argument("--input", required=True)
    p_recommender.add_argument("--input-type", type=int, choices=[1, 2])
    p_recommender.add_argument("--output-type", type=int, choices=[1, 2])
    p_recommender.add_argument("--max-elements-set", type=int, choices=[2, 3, 4])
    p_recommender.add_argument("--wc", type=float)
    p_recommender.add_argument("--wa", type=float)
    p_recommender.add_argument("--wd", type=float)
    p_recommender.add_argument("--ws", type=float)
    p_recommender.add_argument("--ontologies")

    p_batch = sub.add_parser("batch", help="Batch operations")
    batch_sub = p_batch.add_subparsers(dest="batch_cmd", required=True)
    p_batch_classes = batch_sub.add_parser("classes", help="Batch class lookup")
    _add_data_flags(p_batch_classes)

    p_analytics = sub.add_parser("analytics", help="Analytics endpoints")
    analytics_sub = p_analytics.add_subparsers(dest="analytics_cmd", required=True)
    p_analytics_global = analytics_sub.add_parser("global", help="Global analytics")
    _add_common_query_flags(p_analytics_global)
    p_analytics_global.add_argument("--month", type=int)
    p_analytics_global.add_argument("--year", type=int)
    p_analytics_onto = analytics_sub.add_parser("ontology", help="Ontology analytics")
    _add_common_query_flags(p_analytics_onto)
    p_analytics_onto.add_argument("acronym")

    p_ont = sub.add_parser("ontologies", help="Ontology endpoints")
    ont_sub = p_ont.add_subparsers(dest="ont_cmd", required=True)
    for cmd in ["list", "full"]:
        p = ont_sub.add_parser(cmd, help=f"{cmd} ontologies")
        _add_common_query_flags(p)
    p = ont_sub.add_parser("get", help="Get ontology")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = ont_sub.add_parser("create", help="Create ontology")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = ont_sub.add_parser("put", help="Put ontology")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    _add_data_flags(p)
    p = ont_sub.add_parser("patch", help="Patch ontology")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    _add_data_flags(p)
    p = ont_sub.add_parser("delete", help="Delete ontology")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = ont_sub.add_parser("latest-submission", help="Get latest ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = ont_sub.add_parser("download", help="Download ontology file")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = ont_sub.add_parser("admin-log", help="Ontology admin log")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = ont_sub.add_parser("pull", help="Trigger ontology pull")
    _add_common_query_flags(p)
    p.add_argument("acronym")

    p_subs = sub.add_parser("submissions", help="Submission endpoints")
    subs_sub = p_subs.add_subparsers(dest="subs_cmd", required=True)
    p = subs_sub.add_parser("list", help="List global submissions")
    _add_common_query_flags(p)
    p = subs_sub.add_parser("create", help="Create global submission")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = subs_sub.add_parser("ontology-list", help="List ontology submissions")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = subs_sub.add_parser("ontology-create", help="Create ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    _add_data_flags(p)
    p = subs_sub.add_parser("ontology-delete", help="Delete ontology submissions")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p = subs_sub.add_parser("get", help="Get ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("submission_id")
    p = subs_sub.add_parser("patch", help="Patch ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("submission_id")
    _add_data_flags(p)
    p = subs_sub.add_parser("delete", help="Delete ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("submission_id")
    p = subs_sub.add_parser("download", help="Download ontology submission")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("submission_id")
    p = subs_sub.add_parser("download-diff", help="Download ontology submission diff")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("submission_id")
    p = subs_sub.add_parser("bulk-delete-status", help="Get bulk delete process status")
    _add_common_query_flags(p)
    p.add_argument("acronym")
    p.add_argument("process_id")

    p_classes = sub.add_parser("classes", help="Class endpoints")
    classes_sub = p_classes.add_subparsers(dest="classes_cmd", required=True)
    for cmd in ["list", "roots", "roots-paged"]:
        p = classes_sub.add_parser(cmd, help=f"{cmd} classes")
        _add_common_query_flags(p)
        p.add_argument("ontology")
    for cmd in [
        "get",
        "paths-to-root",
        "tree",
        "ancestors",
        "descendants",
        "children",
        "parents",
        "instances",
        "mappings",
        "notes",
    ]:
        p = classes_sub.add_parser(cmd, help=f"Class {cmd}")
        _add_common_query_flags(p)
        p.add_argument("ontology")
        p.add_argument("class_id")
        if cmd == "notes":
            p.add_argument("--include-threads", action=argparse.BooleanOptionalAction, default=None)

    p_props = sub.add_parser("properties", help="Property endpoints")
    props_sub = p_props.add_subparsers(dest="props_cmd", required=True)
    for cmd in ["list", "roots"]:
        p = props_sub.add_parser(cmd, help=f"{cmd} properties")
        _add_common_query_flags(p)
        p.add_argument("ontology")
    for cmd in ["get", "label", "tree", "ancestors", "descendants", "parents", "children"]:
        p = props_sub.add_parser(cmd, help=f"Property {cmd}")
        _add_common_query_flags(p)
        p.add_argument("ontology")
        p.add_argument("property_id")

    p_inst = sub.add_parser("instances", help="Instance endpoints")
    inst_sub = p_inst.add_subparsers(dest="inst_cmd", required=True)
    p = inst_sub.add_parser("list", help="List instances")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = inst_sub.add_parser("get", help="Get instance")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("instance_id")
    p = inst_sub.add_parser("class-list", help="List instances for class")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("class_id")

    p_col = sub.add_parser("collections", help="Collection endpoints")
    col_sub = p_col.add_subparsers(dest="col_cmd", required=True)
    p = col_sub.add_parser("list", help="List collections")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = col_sub.add_parser("get", help="Get collection")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("collection_id")
    p = col_sub.add_parser("members", help="List collection members")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("collection_id")

    p_schemes = sub.add_parser("schemes", help="Scheme endpoints")
    schemes_sub = p_schemes.add_subparsers(dest="schemes_cmd", required=True)
    p = schemes_sub.add_parser("list", help="List schemes")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = schemes_sub.add_parser("get", help="Get scheme")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("scheme_id")

    p_map = sub.add_parser("mappings", help="Mapping endpoints")
    map_sub = p_map.add_subparsers(dest="map_cmd", required=True)
    for cmd in ["list", "recent", "stats-ontologies"]:
        p = map_sub.add_parser(cmd, help=f"{cmd} mappings")
        _add_common_query_flags(p)
    p = map_sub.add_parser("stats-ontology", help="Get mapping stats for ontology")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = map_sub.add_parser("get", help="Get mapping")
    _add_common_query_flags(p)
    p.add_argument("mapping_id")
    p = map_sub.add_parser("delete", help="Delete mapping")
    _add_common_query_flags(p)
    p.add_argument("mapping_id")
    p = map_sub.add_parser("create", help="Create mapping")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = map_sub.add_parser("ontology-list", help="List mappings for ontology")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = map_sub.add_parser("class-list", help="List mappings for class")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("class_id")

    p_metrics = sub.add_parser("metrics", help="Metrics endpoints")
    metrics_sub = p_metrics.add_subparsers(dest="metrics_cmd", required=True)
    for cmd in ["list", "missing"]:
        p = metrics_sub.add_parser(cmd, help=f"{cmd} metrics")
        _add_common_query_flags(p)
    p = metrics_sub.add_parser("ontology", help="Get ontology metrics")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = metrics_sub.add_parser("submission", help="Get submission metrics")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("submission_id")

    p_workflows = sub.add_parser("workflows", help="Higher-order workflow commands")
    wf_sub = p_workflows.add_subparsers(dest="wf_cmd", required=True)

    p = wf_sub.add_parser("concept-resolve", help="Resolve concept by ID or search")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("term_or_id")
    p.add_argument("--search-limit", type=int, default=5)
    p.add_argument("--require-exact-match", action=argparse.BooleanOptionalAction, default=True)

    p = wf_sub.add_parser("concept-expand", help="Expand concept neighborhood graph")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p.add_argument("class_id")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--include-ancestors", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-descendants", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-paths", action=argparse.BooleanOptionalAction, default=True)

    p = wf_sub.add_parser("concept-annotate-and-map", help="Annotate text and expand with mappings")
    _add_common_query_flags(p)
    p.add_argument("--text", required=True)
    p.add_argument("--ontologies")
    p.add_argument("--semantic-types")
    p.add_argument("--include-class-details", action=argparse.BooleanOptionalAction, default=True)

    p = wf_sub.add_parser("ontology-profile", help="Build ontology profile summary")
    _add_common_query_flags(p)
    p.add_argument("acronym")

    p = wf_sub.add_parser("ontology-compare", help="Compare two ontologies")
    _add_common_query_flags(p)
    p.add_argument("left")
    p.add_argument("right")
    p.add_argument("--by", choices=["metrics", "mappings", "coverage", "all"], default="all")
    p.add_argument(
        "--probe",
        action="append",
        help="Coverage probe query (repeatable; used for --by coverage/all)",
    )

    p = wf_sub.add_parser(
        "recommender-explain", help="Run recommender and include explanation summary"
    )
    _add_common_query_flags(p)
    p.add_argument("--input", required=True)
    p.add_argument("--input-type", type=int, choices=[1, 2])
    p.add_argument("--output-type", type=int, choices=[1, 2])
    p.add_argument("--max-elements-set", type=int, choices=[2, 3, 4])
    p.add_argument("--wc", type=float)
    p.add_argument("--wa", type=float)
    p.add_argument("--wd", type=float)
    p.add_argument("--ws", type=float)
    p.add_argument("--ontologies")

    p = wf_sub.add_parser(
        "notes-thread-export", help="Export notes and replies as normalized threads"
    )
    _add_common_query_flags(p)
    p.add_argument("--ontology")
    p.add_argument("--class-id")
    p.add_argument("--global", dest="global_scope", action="store_true")

    p = wf_sub.add_parser("batch-classes-from-file", help="Build /batch class payload from file")
    _add_common_query_flags(p)
    p.add_argument("input_file")
    p.add_argument("--display", default="prefLabel,synonym,semanticTypes")

    p = wf_sub.add_parser("fetch-all", help="Fetch all pages from a list endpoint")
    _add_common_query_flags(p)
    p.add_argument("path", help="API path for list endpoint, e.g. /ontologies")
    p.add_argument("--query", action="append", help="Query key=value (repeatable)")
    p.add_argument("--max-pages", type=int)

    p = wf_sub.add_parser(
        "pipeline-suggest-ontologies",
        help="Recommend ontologies and run quick search/annotation previews",
    )
    _add_common_query_flags(p)
    p.add_argument("--text", required=True)
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--search-pagesize", type=int, default=3)

    _register_discussion_family(
        sub,
        "notes",
        singular="note",
        include_threads=True,
        ontology_prefix=True,
        class_prefix=True,
    )
    _register_discussion_family(
        sub,
        "replies",
        singular="reply",
        include_threads=True,
        note_prefix=True,
    )
    _register_discussion_family(
        sub,
        "reviews",
        singular="review",
        include_threads=False,
        acronym_prefix=True,
    )

    p_pc = sub.add_parser("provisional-classes", help="Provisional class endpoints")
    pc_sub = p_pc.add_subparsers(dest="provisional_classes_cmd", required=True)
    p = pc_sub.add_parser("list", help="List provisional classes")
    _add_common_query_flags(p)
    p = pc_sub.add_parser("create", help="Create provisional class")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = pc_sub.add_parser("get", help="Get provisional class")
    _add_common_query_flags(p)
    p.add_argument("provisional_class_id")
    p = pc_sub.add_parser("patch", help="Patch provisional class")
    _add_common_query_flags(p)
    p.add_argument("provisional_class_id")
    _add_data_flags(p)
    p = pc_sub.add_parser("delete", help="Delete provisional class")
    _add_common_query_flags(p)
    p.add_argument("provisional_class_id")
    p = pc_sub.add_parser("ontology-list", help="List provisional classes for ontology")
    _add_common_query_flags(p)
    p.add_argument("ontology")
    p = pc_sub.add_parser("user-list", help="List provisional classes for user")
    _add_common_query_flags(p)
    p.add_argument("user")

    p_pr = sub.add_parser("provisional-relations", help="Provisional relation endpoints")
    pr_sub = p_pr.add_subparsers(dest="provisional_relations_cmd", required=True)
    p = pr_sub.add_parser("list", help="List provisional relations")
    _add_common_query_flags(p)
    p = pr_sub.add_parser("create", help="Create provisional relation")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = pr_sub.add_parser("get", help="Get provisional relation")
    _add_common_query_flags(p)
    p.add_argument("provisional_relation_id")
    p = pr_sub.add_parser("delete", help="Delete provisional relation")
    _add_common_query_flags(p)
    p.add_argument("provisional_relation_id")

    _register_meta_family(sub, "categories")
    _register_meta_family(sub, "groups")
    _register_meta_family(sub, "projects")

    p_slices = sub.add_parser("slices", help="Slice endpoints")
    slices_sub = p_slices.add_subparsers(dest="slices_cmd", required=True)
    for cmd in ["list", "sync-groups"]:
        p = slices_sub.add_parser(cmd, help=f"{cmd} slices")
        _add_common_query_flags(p)
    p = slices_sub.add_parser("create", help="Create slice")
    _add_common_query_flags(p)
    _add_data_flags(p)
    p = slices_sub.add_parser("get", help="Get slice")
    _add_common_query_flags(p)
    p.add_argument("slice_id")
    p = slices_sub.add_parser("patch", help="Patch slice")
    _add_common_query_flags(p)
    p.add_argument("slice_id")
    _add_data_flags(p)
    p = slices_sub.add_parser("delete", help="Delete slice")
    _add_common_query_flags(p)
    p.add_argument("slice_id")

    p_users = sub.add_parser("users", help="User endpoints")
    users_sub = p_users.add_subparsers(dest="users_cmd", required=True)
    for cmd in ["list"]:
        p = users_sub.add_parser(cmd, help=f"{cmd} users")
        _add_common_query_flags(p)
    for cmd in ["create", "authenticate", "create-reset-password-token", "reset-password"]:
        p = users_sub.add_parser(cmd, help=f"{cmd} users")
        _add_common_query_flags(p)
        _add_data_flags(p)
    p = users_sub.add_parser("get", help="Get user")
    _add_common_query_flags(p)
    p.add_argument("username")
    p = users_sub.add_parser("put", help="Put user")
    _add_common_query_flags(p)
    p.add_argument("username")
    _add_data_flags(p)
    p = users_sub.add_parser("patch", help="Patch user")
    _add_common_query_flags(p)
    p.add_argument("username")
    _add_data_flags(p)
    p = users_sub.add_parser("delete", help="Delete user")
    _add_common_query_flags(p)
    p.add_argument("username")

    return parser


def _register_meta_family(root_sub: Any, name: str) -> None:
    p = root_sub.add_parser(name, help=f"{name} endpoints")
    sub = p.add_subparsers(dest=f"{name}_cmd", required=True)
    for cmd in ["list", "create", "get", "put", "patch", "delete", "ontology-list"]:
        x = sub.add_parser(cmd, help=f"{cmd} {name}")
        _add_common_query_flags(x)
        if cmd in {"create", "put", "patch"}:
            _add_data_flags(x)
        if cmd in {"get", "put", "patch", "delete"}:
            x.add_argument("acronym")
        if cmd == "ontology-list":
            x.add_argument("ontology")


def _register_discussion_family(
    root_sub: Any,
    name: str,
    singular: str,
    *,
    include_threads: bool,
    ontology_prefix: bool = False,
    class_prefix: bool = False,
    note_prefix: bool = False,
    acronym_prefix: bool = False,
) -> None:
    p = root_sub.add_parser(name, help=f"{name} endpoints")
    sub = p.add_subparsers(dest=f"{name}_cmd", required=True)
    for cmd in ["list", "create", "get", "patch", "delete"]:
        x = sub.add_parser(cmd, help=f"{cmd} {name}")
        _add_common_query_flags(x)
        if cmd in {"create", "patch"}:
            _add_data_flags(x)
        if cmd in {"get", "patch", "delete"}:
            x.add_argument(f"{singular}_id")
        if include_threads and cmd == "list":
            x.add_argument("--include-threads", action=argparse.BooleanOptionalAction, default=None)
        if include_threads and cmd == "get":
            x.add_argument("--include-threads", action=argparse.BooleanOptionalAction, default=None)
    if ontology_prefix:
        x = sub.add_parser("ontology-list", help=f"List {name} for ontology")
        _add_common_query_flags(x)
        x.add_argument("ontology")
        if name == "notes":
            x.add_argument("--include-threads", action=argparse.BooleanOptionalAction, default=None)
    if class_prefix:
        x = sub.add_parser("class-list", help=f"List {name} for class")
        _add_common_query_flags(x)
        x.add_argument("ontology")
        x.add_argument("class_id")
        if name == "notes":
            x.add_argument("--include-threads", action=argparse.BooleanOptionalAction, default=None)
    if note_prefix:
        x = sub.add_parser("note-list", help=f"List {name} for note")
        _add_common_query_flags(x)
        x.add_argument("note_id")
    if acronym_prefix:
        x = sub.add_parser("ontology-list", help=f"List {name} for ontology acronym")
        _add_common_query_flags(x)
        x.add_argument("acronym")


def dispatch(args: argparse.Namespace, config: Config) -> CommandResult:
    if args.command == "docs":
        if args.docs_cmd == "info":
            return CommandResult(payload=docs_info())
        if args.docs_cmd == "catalog":
            return CommandResult(payload=endpoint_catalog())
        if args.docs_cmd == "families":
            return CommandResult(payload=endpoint_families())
        raise ValueError("unknown docs command")

    if args.command == "config":
        if args.config_cmd == "show":
            return CommandResult(
                payload={
                    "base_url": config.base_url,
                    "timeout": config.timeout,
                    "api_key_present": config.api_key is not None,
                }
            )
        if args.config_cmd == "set":
            path = write_config(api_key=args.api_key, base_url=args.base_url, timeout=args.timeout)
            return CommandResult(payload={"config_path": str(path), "updated": True})
        raise ValueError("unknown config command")

    with BioPortalClient(
        base_url=config.base_url, api_key=config.api_key, timeout=config.timeout
    ) as client:
        return _dispatch_with_client(client, args)


def _dispatch_with_client(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    if args.command == "api" and args.api_cmd == "request":
        query_pairs = args.query
        params: dict[str, str] = {}
        for item in query_pairs or []:
            if "=" not in item:
                raise ValueError(f"invalid key=value entry: {item}")
            key, value = item.split("=", 1)
            if key.strip() == "":
                raise ValueError(f"invalid key=value entry: {item}")
            params[key] = value
        body = _load_json_body(args)
        if args.binary:
            binary_payload = client.request_bytes(args.method.upper(), args.path, params=params)
            return CommandResult(payload=binary_payload, is_binary=True)
        if args.raw:
            raw_payload = client.request_raw(args.method.upper(), args.path, params=params)
            return CommandResult(payload=raw_payload)
        envelope = client.request(args.method.upper(), args.path, params=params, json_body=body)
        return CommandResult(payload=envelope.data)

    if args.command == "search":
        params = {
            "q": args.q,
            "ontologies": args.ontologies,
            "require_exact_match": args.require_exact_match,
            "suggest": args.suggest,
            "also_search_views": args.also_search_views,
            "require_definitions": args.require_definitions,
            "also_search_properties": args.also_search_properties,
            "also_search_obsolete": args.also_search_obsolete,
            "cui": args.cui,
            "semantic_types": args.semantic_types,
            "language": args.language,
            "ontology": args.ontology,
            "subtree_root_id": args.subtree_root_id,
            "roots_only": args.roots_only,
        }
        return _run_request(client, args=args, method="GET", path="/search", params=params)

    if args.command == "property-search":
        params = {
            "q": args.q,
            "ontologies": args.ontologies,
            "require_exact_match": args.require_exact_match,
            "also_search_views": args.also_search_views,
            "require_definitions": args.require_definitions,
            "ontology_types": args.ontology_types,
            "property_types": args.property_types,
        }
        return _run_request(client, args=args, method="GET", path="/property_search", params=params)

    if args.command == "annotator":
        params = {
            "text": args.text,
            "ontologies": args.ontologies,
            "semantic_types": args.semantic_types,
            "expand_semantic_types_hierarchy": args.expand_semantic_types_hierarchy,
            "expand_class_hierarchy": args.expand_class_hierarchy,
            "class_hierarchy_max_level": args.class_hierarchy_max_level,
            "expand_mappings": args.expand_mappings,
            "stop_words": args.stop_words,
            "minimum_match_length": args.minimum_match_length,
            "exclude_numbers": args.exclude_numbers,
            "whole_word_only": args.whole_word_only,
            "exclude_synonyms": args.exclude_synonyms,
            "longest_only": args.longest_only,
        }
        return _run_request(client, args=args, method="GET", path="/annotator", params=params)

    if args.command == "recommender":
        params = {
            "input": args.input,
            "input_type": args.input_type,
            "output_type": args.output_type,
            "max_elements_set": args.max_elements_set,
            "wc": args.wc,
            "wa": args.wa,
            "wd": args.wd,
            "ws": args.ws,
            "ontologies": args.ontologies,
        }
        return _run_request(client, args=args, method="GET", path="/recommender", params=params)

    if args.command == "batch" and args.batch_cmd == "classes":
        body = _load_json_body(args)
        return _run_request(client, args=args, method="POST", path="/batch", json_body=body)

    if args.command == "analytics":
        if args.analytics_cmd == "global":
            return _run_request(
                client,
                args=args,
                method="GET",
                path="/analytics",
                params={"month": args.month, "year": args.year},
            )
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/analytics",
        )

    if args.command == "ontologies":
        return _dispatch_ontologies(client, args)
    if args.command == "submissions":
        return _dispatch_submissions(client, args)
    if args.command == "classes":
        return _dispatch_classes(client, args)
    if args.command == "properties":
        return _dispatch_properties(client, args)
    if args.command == "instances":
        return _dispatch_instances(client, args)
    if args.command == "collections":
        return _dispatch_collections(client, args)
    if args.command == "schemes":
        return _dispatch_schemes(client, args)
    if args.command == "mappings":
        return _dispatch_mappings(client, args)
    if args.command == "metrics":
        return _dispatch_metrics(client, args)
    if args.command == "workflows":
        return _dispatch_workflows(client, args)
    if args.command == "notes":
        return _dispatch_notes(client, args)
    if args.command == "replies":
        return _dispatch_replies(client, args)
    if args.command == "reviews":
        return _dispatch_reviews(client, args)
    if args.command == "provisional-classes":
        return _dispatch_provisional_classes(client, args)
    if args.command == "provisional-relations":
        return _dispatch_provisional_relations(client, args)
    if args.command == "categories":
        return _dispatch_meta_family(client, args, family="categories")
    if args.command == "groups":
        return _dispatch_meta_family(client, args, family="groups")
    if args.command == "projects":
        return _dispatch_meta_family(client, args, family="projects")
    if args.command == "slices":
        return _dispatch_slices(client, args)
    if args.command == "users":
        return _dispatch_users(client, args)
    raise ValueError("unknown command")


def _dispatch_ontologies(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.ont_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/ontologies")
    if cmd == "full":
        return _run_request(client, args=args, method="GET", path="/ontologies_full")
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/ontologies/{args.acronym}")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/ontologies", json_body=_load_json_body(args)
        )
    if cmd == "put":
        return _run_request(
            client,
            args=args,
            method="PUT",
            path=f"/ontologies/{args.acronym}",
            json_body=_load_json_body(args),
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/ontologies/{args.acronym}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/ontologies/{args.acronym}")
    if cmd == "latest-submission":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.acronym}/latest_submission"
        )
    if cmd == "download":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/download",
            binary=True,
        )
    if cmd == "admin-log":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.acronym}/admin/log"
        )
    if cmd == "pull":
        return _run_request(
            client, args=args, method="POST", path=f"/ontologies/{args.acronym}/pull"
        )
    raise ValueError("unknown ontologies command")


def _dispatch_submissions(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.subs_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/submissions")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/submissions", json_body=_load_json_body(args)
        )
    if cmd == "ontology-list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.acronym}/submissions"
        )
    if cmd == "ontology-create":
        return _run_request(
            client,
            args=args,
            method="POST",
            path=f"/ontologies/{args.acronym}/submissions",
            json_body=_load_json_body(args),
        )
    if cmd == "ontology-delete":
        return _run_request(
            client, args=args, method="DELETE", path=f"/ontologies/{args.acronym}/submissions"
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/submissions/{args.submission_id}",
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/ontologies/{args.acronym}/submissions/{args.submission_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(
            client,
            args=args,
            method="DELETE",
            path=f"/ontologies/{args.acronym}/submissions/{args.submission_id}",
        )
    if cmd == "download":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/submissions/{args.submission_id}/download",
            binary=True,
        )
    if cmd == "download-diff":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/submissions/{args.submission_id}/download_diff",
            binary=True,
        )
    if cmd == "bulk-delete-status":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.acronym}/submissions/bulk_delete/{args.process_id}",
        )
    raise ValueError("unknown submissions command")


def _dispatch_classes(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.classes_cmd
    if cmd == "list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/classes"
        )
    if cmd == "roots":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/classes/roots"
        )
    if cmd == "roots-paged":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/classes/roots_paged"
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}",
        )
    if cmd == "paths-to-root":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/paths_to_root",
        )
    if cmd == "tree":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/tree",
        )
    if cmd == "ancestors":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/ancestors",
        )
    if cmd == "descendants":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/descendants",
        )
    if cmd == "children":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/children",
        )
    if cmd == "parents":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/parents",
        )
    if cmd == "instances":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/instances",
        )
    if cmd == "mappings":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/mappings",
        )
    if cmd == "notes":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/notes",
            params={"include_threads": args.include_threads},
        )
    raise ValueError("unknown classes command")


def _dispatch_properties(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.props_cmd
    base = f"/ontologies/{args.ontology}/properties"
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path=base)
    if cmd == "roots":
        return _run_request(client, args=args, method="GET", path=f"{base}/roots")
    item = f"{base}/{args.property_id}"
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=item)
    if cmd == "label":
        return _run_request(client, args=args, method="GET", path=f"{item}/label")
    if cmd == "tree":
        return _run_request(client, args=args, method="GET", path=f"{item}/tree")
    if cmd == "ancestors":
        return _run_request(client, args=args, method="GET", path=f"{item}/ancestors")
    if cmd == "descendants":
        return _run_request(client, args=args, method="GET", path=f"{item}/descendants")
    if cmd == "parents":
        return _run_request(client, args=args, method="GET", path=f"{item}/parents")
    if cmd == "children":
        return _run_request(client, args=args, method="GET", path=f"{item}/children")
    raise ValueError("unknown properties command")


def _dispatch_instances(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    if args.inst_cmd == "list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/instances"
        )
    if args.inst_cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/instances/{args.instance_id}",
        )
    if args.inst_cmd == "class-list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/instances",
        )
    raise ValueError("unknown instances command")


def _dispatch_collections(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    if args.col_cmd == "list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/collections"
        )
    if args.col_cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/collections/{args.collection_id}",
        )
    if args.col_cmd == "members":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/collections/{args.collection_id}/members",
        )
    raise ValueError("unknown collections command")


def _dispatch_schemes(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    if args.schemes_cmd == "list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/schemes"
        )
    if args.schemes_cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/schemes/{args.scheme_id}",
        )
    raise ValueError("unknown schemes command")


def _dispatch_mappings(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.map_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/mappings")
    if cmd == "recent":
        return _run_request(client, args=args, method="GET", path="/mappings/recent")
    if cmd == "stats-ontologies":
        return _run_request(client, args=args, method="GET", path="/mappings/statistics/ontologies")
    if cmd == "stats-ontology":
        return _run_request(
            client, args=args, method="GET", path=f"/mappings/statistics/ontologies/{args.ontology}"
        )
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/mappings/{args.mapping_id}")
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/mappings/{args.mapping_id}")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/mappings", json_body=_load_json_body(args)
        )
    if cmd == "ontology-list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/mappings"
        )
    if cmd == "class-list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/mappings",
        )
    raise ValueError("unknown mappings command")


def _dispatch_metrics(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    if args.metrics_cmd == "list":
        return _run_request(client, args=args, method="GET", path="/metrics")
    if args.metrics_cmd == "missing":
        return _run_request(client, args=args, method="GET", path="/metrics/missing")
    if args.metrics_cmd == "ontology":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/metrics"
        )
    if args.metrics_cmd == "submission":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/submissions/{args.submission_id}/metrics",
        )
    raise ValueError("unknown metrics command")


def _dispatch_workflows(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.wf_cmd
    if cmd == "concept-resolve":
        ontology = _enc(args.ontology)
        term_or_id = args.term_or_id
        looked_up_by_id = False
        direct_payload: Any | None = None

        if term_or_id.startswith("http://") or term_or_id.startswith("https://"):
            looked_up_by_id = True
            try:
                direct_payload = client.request(
                    "GET",
                    f"/ontologies/{ontology}/classes/{_enc(term_or_id)}",
                    params=common_params(args),
                ).data
            except BioPortalError:
                direct_payload = None

        if direct_payload is not None:
            return CommandResult(
                payload={
                    "strategy": "direct-class-id",
                    "ontology": args.ontology,
                    "query": term_or_id,
                    "resolved": direct_payload,
                }
            )

        resolve_params = {
            **common_params(args),
            "q": term_or_id,
            "ontology": args.ontology,
            "require_exact_match": args.require_exact_match,
            "pagesize": args.search_limit,
        }
        results = client.request("GET", "/search", params=resolve_params).data
        if isinstance(results, list) and results:
            return CommandResult(
                payload={
                    "strategy": "search",
                    "looked_up_by_id": looked_up_by_id,
                    "ontology": args.ontology,
                    "query": term_or_id,
                    "best_match": results[0],
                    "candidates": results,
                }
            )
        return CommandResult(
            payload={
                "strategy": "search",
                "ontology": args.ontology,
                "query": term_or_id,
                "resolved": None,
                "candidates": [],
            }
        )

    if cmd == "concept-expand":
        ontology = _enc(args.ontology)
        class_id = _enc(args.class_id)
        base = f"/ontologies/{ontology}/classes/{class_id}"
        node = client.request("GET", base, params=common_params(args)).data
        parents = client.request("GET", f"{base}/parents", params=common_params(args)).data
        children = client.request("GET", f"{base}/children", params=common_params(args)).data
        ancestors: Any = []
        descendants: Any = []
        paths_to_root: Any = []
        if args.include_ancestors:
            ancestors = client.request("GET", f"{base}/ancestors", params=common_params(args)).data
        if args.include_descendants:
            descendants = client.request(
                "GET", f"{base}/descendants", params=common_params(args)
            ).data
        if args.include_paths:
            paths_to_root = client.request(
                "GET", f"{base}/paths_to_root", params=common_params(args)
            ).data
        return CommandResult(
            payload={
                "ontology": args.ontology,
                "class_id": args.class_id,
                "depth_requested": args.depth,
                "node": node,
                "neighbors": {"parents": parents, "children": children},
                "ancestors": ancestors,
                "descendants": descendants,
                "paths_to_root": paths_to_root,
            }
        )

    if cmd == "concept-annotate-and-map":
        params = {
            **common_params(args),
            "text": args.text,
            "ontologies": args.ontologies,
            "semantic_types": args.semantic_types,
        }
        annotations = client.request("GET", "/annotator", params=params).data
        enriched: list[dict[str, Any]] = []
        if isinstance(annotations, list):
            for item in annotations:
                if not isinstance(item, dict):
                    continue
                annotated_class = item.get("annotatedClass")
                class_links = (
                    annotated_class.get("links", {}) if isinstance(annotated_class, dict) else {}
                )
                class_self = class_links.get("self") if isinstance(class_links, dict) else None
                class_data: Any | None = None
                mapping_data: Any | None = None
                if isinstance(class_self, str):
                    path = urlparse(class_self).path
                    if args.include_class_details:
                        class_data = client.request("GET", path, params=common_params(args)).data
                    try:
                        mapping_data = client.request(
                            "GET", f"{path}/mappings", params=common_params(args)
                        ).data
                    except BioPortalError:
                        mapping_data = []
                enriched.append(
                    {
                        "annotation": item,
                        "class": class_data,
                        "mappings": mapping_data,
                    }
                )
        return CommandResult(
            payload={"text": args.text, "annotations": annotations, "enriched": enriched}
        )

    if cmd == "ontology-profile":
        acronym = _enc(args.acronym)
        params = common_params(args)
        profile = {
            "ontology": client.request("GET", f"/ontologies/{acronym}", params=params).data,
            "latest_submission": client.request(
                "GET", f"/ontologies/{acronym}/latest_submission", params=params
            ).data,
            "metrics": client.request("GET", f"/ontologies/{acronym}/metrics", params=params).data,
            "analytics": client.request(
                "GET", f"/ontologies/{acronym}/analytics", params=params
            ).data,
            "categories": client.request(
                "GET", f"/ontologies/{acronym}/categories", params=params
            ).data,
            "groups": client.request("GET", f"/ontologies/{acronym}/groups", params=params).data,
            "projects": client.request(
                "GET", f"/ontologies/{acronym}/projects", params=params
            ).data,
        }
        return CommandResult(payload=profile)

    if cmd == "ontology-compare":
        params = common_params(args)
        left = _enc(args.left)
        right = _enc(args.right)
        out: dict[str, Any] = {"left": args.left, "right": args.right, "by": args.by}
        if args.by in {"metrics", "all"}:
            out["metrics"] = {
                "left": client.request("GET", f"/ontologies/{left}/metrics", params=params).data,
                "right": client.request("GET", f"/ontologies/{right}/metrics", params=params).data,
            }
        if args.by in {"mappings", "all"}:
            out["mapping_statistics"] = {
                "left": client.request(
                    "GET", f"/mappings/statistics/ontologies/{left}", params=params
                ).data,
                "right": client.request(
                    "GET", f"/mappings/statistics/ontologies/{right}", params=params
                ).data,
            }
        if args.by in {"coverage", "all"}:
            probes = args.probe or ["disease", "cell", "gene"]
            coverage: list[dict[str, Any]] = []
            for probe in probes:
                left_hits_raw = client.request(
                    "GET",
                    "/search",
                    params={**params, "q": probe, "ontology": args.left, "pagesize": 1},
                ).data
                right_hits_raw = client.request(
                    "GET",
                    "/search",
                    params={**params, "q": probe, "ontology": args.right, "pagesize": 1},
                ).data
                coverage.append(
                    {
                        "probe": probe,
                        "left_hits": len(left_hits_raw) if isinstance(left_hits_raw, list) else 0,
                        "right_hits": len(right_hits_raw)
                        if isinstance(right_hits_raw, list)
                        else 0,
                    }
                )
            out["coverage"] = coverage
        return CommandResult(payload=out)

    if cmd == "recommender-explain":
        params = {
            **common_params(args),
            "input": args.input,
            "input_type": args.input_type,
            "output_type": args.output_type,
            "max_elements_set": args.max_elements_set,
            "wc": args.wc,
            "wa": args.wa,
            "wd": args.wd,
            "ws": args.ws,
            "ontologies": args.ontologies,
        }
        result = client.request("GET", "/recommender", params=params).data
        return CommandResult(
            payload={
                "input": args.input,
                "weights": {
                    "wc": args.wc if args.wc is not None else 0.55,
                    "wa": args.wa if args.wa is not None else 0.15,
                    "wd": args.wd if args.wd is not None else 0.15,
                    "ws": args.ws if args.ws is not None else 0.15,
                },
                "result": result,
            }
        )

    if cmd == "notes-thread-export":
        params = {**common_params(args), "include_threads": True}
        if args.class_id and not args.ontology:
            raise ValueError("--class-id requires --ontology")
        if args.global_scope:
            notes = client.request("GET", "/notes", params=params).data
        elif args.ontology and args.class_id:
            notes = client.request(
                "GET",
                f"/ontologies/{_enc(args.ontology)}/classes/{_enc(args.class_id)}/notes",
                params=params,
            ).data
        elif args.ontology:
            notes = client.request(
                "GET", f"/ontologies/{_enc(args.ontology)}/notes", params=params
            ).data
        else:
            raise ValueError("choose one scope: --global OR --ontology [--class-id]")
        flattened: list[dict[str, Any]] = []
        if isinstance(notes, list):
            for note in notes:
                if not isinstance(note, dict):
                    continue
                note_id = note.get("@id") or note.get("id")
                thread_replies = note.get("replies") or note.get("reply") or []
                flattened.append(
                    {
                        "note_id": note_id,
                        "subject": note.get("subject"),
                        "body": note.get("body"),
                        "reply_count": len(thread_replies)
                        if isinstance(thread_replies, list)
                        else 0,
                        "thread": thread_replies,
                    }
                )
        return CommandResult(payload={"notes": notes, "export": flattened})

    if cmd == "batch-classes-from-file":
        src = Path(args.input_file)
        text = src.read_text(encoding="utf-8")
        collection: list[dict[str, str]] = []
        if src.suffix.lower() == ".json":
            parsed = json.loads(text)
            if isinstance(parsed, list):
                for row in parsed:
                    if isinstance(row, dict) and "class" in row and "ontology" in row:
                        collection.append(
                            {
                                "class": str(row["class"]),
                                "ontology": str(row["ontology"]),
                            }
                        )
            else:
                raise ValueError("JSON input must be a list of {'class','ontology'} objects")
        else:
            for line in text.splitlines():
                stripped = line.strip()
                if stripped == "" or stripped.startswith("#"):
                    continue
                if "," not in stripped:
                    raise ValueError("CSV input lines must be: class,ontology")
                cls, ont = stripped.split(",", 1)
                collection.append({"class": cls.strip(), "ontology": ont.strip()})
        payload = {
            "http://www.w3.org/2002/07/owl#Class": {
                "collection": collection,
                "display": args.display,
            }
        }
        result = client.request(
            "POST", "/batch", json_body=payload, params=common_params(args)
        ).data
        return CommandResult(payload={"request": payload, "result": result})

    if cmd == "fetch-all":
        fetch_params: dict[str, Any] = common_params(args)
        for pair in args.query or []:
            if "=" not in pair:
                raise ValueError(f"invalid key=value entry: {pair}")
            key, value = pair.split("=", 1)
            if key.strip() == "":
                raise ValueError(f"invalid key=value entry: {pair}")
            fetch_params[key] = value
        items = client.paginate(args.path, params=fetch_params, max_pages=args.max_pages)
        return CommandResult(
            payload={
                "path": args.path,
                "max_pages": args.max_pages,
                "count": len(items),
                "items": items,
            }
        )

    if cmd == "pipeline-suggest-ontologies":
        params = common_params(args)
        rec = client.request("GET", "/recommender", params={**params, "input": args.text}).data
        top_candidates: list[dict[str, Any]] = []
        if isinstance(rec, list):
            top_candidates = [x for x in rec if isinstance(x, dict)][: args.top]
        previews: list[dict[str, Any]] = []
        for item in top_candidates:
            ontology_acronym: str | None = None
            if isinstance(item.get("ontology"), dict):
                ontology_acronym = item["ontology"].get("acronym")
            ontology_acronym = ontology_acronym or item.get("acronym")
            if not isinstance(ontology_acronym, str):
                continue
            search_preview = client.request(
                "GET",
                "/search",
                params={
                    **params,
                    "q": args.text,
                    "ontology": ontology_acronym,
                    "pagesize": args.search_pagesize,
                },
            ).data
            annotation_preview = client.request(
                "GET",
                "/annotator",
                params={**params, "text": args.text, "ontologies": ontology_acronym},
            ).data
            previews.append(
                {
                    "ontology": ontology_acronym,
                    "search_preview": search_preview,
                    "annotation_preview": annotation_preview,
                }
            )
        return CommandResult(
            payload={
                "input_text": args.text,
                "recommended": rec,
                "top_considered": [p["ontology"] for p in previews],
                "previews": previews,
            }
        )

    raise ValueError("unknown workflows command")


def _dispatch_notes(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.notes_cmd
    if cmd == "list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path="/notes",
            params={"include_threads": args.include_threads},
        )
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/notes", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/notes/{args.note_id}",
            params={"include_threads": args.include_threads},
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/notes/{args.note_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/notes/{args.note_id}")
    if cmd == "ontology-list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/notes",
            params={"include_threads": args.include_threads},
        )
    if cmd == "class-list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/ontologies/{args.ontology}/classes/{args.class_id}/notes",
            params={"include_threads": args.include_threads},
        )
    raise ValueError("unknown notes command")


def _dispatch_replies(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.replies_cmd
    if cmd == "list":
        return _run_request(
            client,
            args=args,
            method="GET",
            path="/replies",
            params={"include_threads": args.include_threads},
        )
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/replies", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/replies/{args.reply_id}",
            params={"include_threads": args.include_threads},
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/replies/{args.reply_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/replies/{args.reply_id}")
    if cmd == "note-list":
        return _run_request(client, args=args, method="GET", path=f"/notes/{args.note_id}/replies")
    raise ValueError("unknown replies command")


def _dispatch_reviews(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.reviews_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/reviews")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/reviews", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/reviews/{args.review_id}")
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/reviews/{args.review_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/reviews/{args.review_id}")
    if cmd == "ontology-list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.acronym}/reviews"
        )
    raise ValueError("unknown reviews command")


def _dispatch_provisional_classes(
    client: BioPortalClient, args: argparse.Namespace
) -> CommandResult:
    cmd = args.provisional_classes_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/provisional_classes")
    if cmd == "create":
        return _run_request(
            client,
            args=args,
            method="POST",
            path="/provisional_classes",
            json_body=_load_json_body(args),
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/provisional_classes/{args.provisional_class_id}",
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/provisional_classes/{args.provisional_class_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(
            client,
            args=args,
            method="DELETE",
            path=f"/provisional_classes/{args.provisional_class_id}",
        )
    if cmd == "ontology-list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/provisional_classes"
        )
    if cmd == "user-list":
        return _run_request(
            client, args=args, method="GET", path=f"/users/{args.user}/provisional_classes"
        )
    raise ValueError("unknown provisional-classes command")


def _dispatch_provisional_relations(
    client: BioPortalClient, args: argparse.Namespace
) -> CommandResult:
    cmd = args.provisional_relations_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/provisional_relations")
    if cmd == "create":
        return _run_request(
            client,
            args=args,
            method="POST",
            path="/provisional_relations",
            json_body=_load_json_body(args),
        )
    if cmd == "get":
        return _run_request(
            client,
            args=args,
            method="GET",
            path=f"/provisional_relations/{args.provisional_relation_id}",
        )
    if cmd == "delete":
        return _run_request(
            client,
            args=args,
            method="DELETE",
            path=f"/provisional_relations/{args.provisional_relation_id}",
        )
    if cmd == "ontology-list":
        return _run_request(client, args=args, method="GET", path="/provisional_relations")
    if cmd == "user-list":
        return _run_request(client, args=args, method="GET", path="/provisional_relations")
    raise ValueError("unknown provisional-relations command")


def _dispatch_meta_family(
    client: BioPortalClient,
    args: argparse.Namespace,
    *,
    family: str,
) -> CommandResult:
    cmd = getattr(args, f"{family}_cmd")
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path=f"/{family}")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path=f"/{family}", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/{family}/{args.acronym}")
    if cmd == "put":
        return _run_request(
            client,
            args=args,
            method="PUT",
            path=f"/{family}/{args.acronym}",
            json_body=_load_json_body(args),
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/{family}/{args.acronym}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/{family}/{args.acronym}")
    if cmd == "ontology-list":
        return _run_request(
            client, args=args, method="GET", path=f"/ontologies/{args.ontology}/{family}"
        )
    raise ValueError(f"unknown {family} command")


def _dispatch_slices(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.slices_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/slices")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/slices", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/slices/{args.slice_id}")
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/slices/{args.slice_id}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/slices/{args.slice_id}")
    if cmd == "sync-groups":
        return _run_request(client, args=args, method="GET", path="/slices/synchronize_groups")
    raise ValueError("unknown slices command")


def _dispatch_users(client: BioPortalClient, args: argparse.Namespace) -> CommandResult:
    cmd = args.users_cmd
    if cmd == "list":
        return _run_request(client, args=args, method="GET", path="/users")
    if cmd == "create":
        return _run_request(
            client, args=args, method="POST", path="/users", json_body=_load_json_body(args)
        )
    if cmd == "get":
        return _run_request(client, args=args, method="GET", path=f"/users/{args.username}")
    if cmd == "put":
        return _run_request(
            client,
            args=args,
            method="PUT",
            path=f"/users/{args.username}",
            json_body=_load_json_body(args),
        )
    if cmd == "patch":
        return _run_request(
            client,
            args=args,
            method="PATCH",
            path=f"/users/{args.username}",
            json_body=_load_json_body(args),
        )
    if cmd == "delete":
        return _run_request(client, args=args, method="DELETE", path=f"/users/{args.username}")
    if cmd == "authenticate":
        return _run_request(
            client,
            args=args,
            method="POST",
            path="/users/authenticate",
            json_body=_load_json_body(args),
        )
    if cmd == "create-reset-password-token":
        return _run_request(
            client,
            args=args,
            method="POST",
            path="/users/create_reset_password_token",
            json_body=_load_json_body(args),
        )
    if cmd == "reset-password":
        return _run_request(
            client,
            args=args,
            method="POST",
            path="/users/reset_password",
            json_body=_load_json_body(args),
        )
    raise ValueError("unknown users command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 0:
        parser.print_help(sys.stdout)
        return 0

    try:
        try:
            args = parser.parse_args(argv)
        except SystemExit as exc:
            code = exc.code
            if isinstance(code, int):
                return code
            return 1
        config = Config.from_sources(
            cli_api_key=args.api_key,
            cli_base_url=args.base_url,
            cli_timeout=args.timeout,
        )
        result = dispatch(args, config)
        if result.is_binary:
            if args.output_file:
                write_binary_output(result.payload, Path(args.output_file))
                sys.stdout.write(
                    json.dumps({"written": args.output_file, "bytes": len(result.payload)}) + "\n"
                )
                return 0
            sys.stderr.write("error: binary response requires --output-file\n")
            return 2

        output_text = format_output(result.payload, output=args.output)
        if args.output_file:
            Path(args.output_file).write_text(output_text + "\n", encoding="utf-8")
            sys.stdout.write(json.dumps({"written": args.output_file}) + "\n")
        else:
            sys.stdout.write(output_text)
            if not output_text.endswith("\n"):
                sys.stdout.write("\n")
        return 0
    except (ConfigError, BioPortalError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
