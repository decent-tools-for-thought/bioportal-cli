"""Static docs metadata and endpoint catalog for BioPortal CLI."""

from __future__ import annotations

from dataclasses import dataclass

UPSTREAM_DOCS_URL = "https://data.bioontology.org/documentation"


@dataclass(frozen=True)
class EndpointSpec:
    family: str
    method: str
    path: str
    summary: str


ENDPOINT_SPECS: tuple[EndpointSpec, ...] = (
    EndpointSpec("search", "GET/POST", "/search", "Term search"),
    EndpointSpec("search", "GET/POST", "/property_search", "Property search"),
    EndpointSpec("annotator", "GET/POST", "/annotator", "Text annotator"),
    EndpointSpec("recommender", "GET/POST", "/recommender", "Ontology recommender"),
    EndpointSpec("batch", "POST", "/batch", "Batch class lookup"),
    EndpointSpec("analytics", "GET", "/analytics", "Global analytics"),
    EndpointSpec("analytics", "GET", "/ontologies/{acronym}/analytics", "Ontology analytics"),
    EndpointSpec("ontologies", "GET", "/ontologies", "List ontologies"),
    EndpointSpec("ontologies", "POST", "/ontologies", "Create ontology"),
    EndpointSpec("ontologies", "GET/PUT/PATCH/DELETE", "/ontologies/{acronym}", "Ontology item"),
    EndpointSpec("ontologies", "GET", "/ontologies_full", "List full ontologies"),
    EndpointSpec(
        "ontologies", "GET", "/ontologies/{acronym}/latest_submission", "Latest submission"
    ),
    EndpointSpec("ontologies", "GET", "/ontologies/{acronym}/download", "Ontology download"),
    EndpointSpec("ontologies", "GET", "/ontologies/{acronym}/admin/log", "Ontology admin log"),
    EndpointSpec("ontologies", "POST", "/ontologies/{acronym}/pull", "Trigger ontology pull"),
    EndpointSpec("submissions", "GET/POST", "/submissions", "Global submissions"),
    EndpointSpec(
        "submissions",
        "GET/POST/DELETE",
        "/ontologies/{acronym}/submissions",
        "Ontology submissions",
    ),
    EndpointSpec(
        "submissions",
        "GET/PATCH/DELETE",
        "/ontologies/{acronym}/submissions/{submission_id}",
        "Submission item",
    ),
    EndpointSpec(
        "submissions",
        "GET",
        "/ontologies/{acronym}/submissions/{submission_id}/download",
        "Submission download",
    ),
    EndpointSpec(
        "submissions",
        "GET",
        "/ontologies/{acronym}/submissions/{submission_id}/download_diff",
        "Submission diff",
    ),
    EndpointSpec(
        "submissions",
        "GET",
        "/ontologies/{acronym}/submissions/bulk_delete/{process_id}",
        "Bulk delete status",
    ),
    EndpointSpec("classes", "GET", "/ontologies/{ontology}/classes", "List classes"),
    EndpointSpec("classes", "GET", "/ontologies/{ontology}/classes/roots", "Class roots"),
    EndpointSpec(
        "classes", "GET", "/ontologies/{ontology}/classes/roots_paged", "Class roots paged"
    ),
    EndpointSpec("classes", "GET", "/ontologies/{ontology}/classes/{class_id}", "Class item"),
    EndpointSpec(
        "classes",
        "GET",
        "/ontologies/{ontology}/classes/{class_id}/paths_to_root",
        "Class paths to root",
    ),
    EndpointSpec("classes", "GET", "/ontologies/{ontology}/classes/{class_id}/tree", "Class tree"),
    EndpointSpec(
        "classes", "GET", "/ontologies/{ontology}/classes/{class_id}/ancestors", "Class ancestors"
    ),
    EndpointSpec(
        "classes",
        "GET",
        "/ontologies/{ontology}/classes/{class_id}/descendants",
        "Class descendants",
    ),
    EndpointSpec(
        "classes", "GET", "/ontologies/{ontology}/classes/{class_id}/children", "Class children"
    ),
    EndpointSpec(
        "classes", "GET", "/ontologies/{ontology}/classes/{class_id}/parents", "Class parents"
    ),
    EndpointSpec("instances", "GET", "/ontologies/{ontology}/instances", "List instances"),
    EndpointSpec(
        "instances", "GET", "/ontologies/{ontology}/instances/{instance_id}", "Instance item"
    ),
    EndpointSpec(
        "instances", "GET", "/ontologies/{ontology}/classes/{class_id}/instances", "Class instances"
    ),
    EndpointSpec("properties", "GET", "/ontologies/{ontology}/properties", "List properties"),
    EndpointSpec("properties", "GET", "/ontologies/{ontology}/properties/roots", "Property roots"),
    EndpointSpec(
        "properties", "GET", "/ontologies/{ontology}/properties/{property_id}", "Property item"
    ),
    EndpointSpec(
        "properties",
        "GET",
        "/ontologies/{ontology}/properties/{property_id}/label",
        "Property label",
    ),
    EndpointSpec(
        "properties", "GET", "/ontologies/{ontology}/properties/{property_id}/tree", "Property tree"
    ),
    EndpointSpec(
        "properties",
        "GET",
        "/ontologies/{ontology}/properties/{property_id}/ancestors",
        "Property ancestors",
    ),
    EndpointSpec(
        "properties",
        "GET",
        "/ontologies/{ontology}/properties/{property_id}/descendants",
        "Property descendants",
    ),
    EndpointSpec(
        "properties",
        "GET",
        "/ontologies/{ontology}/properties/{property_id}/parents",
        "Property parents",
    ),
    EndpointSpec(
        "properties",
        "GET",
        "/ontologies/{ontology}/properties/{property_id}/children",
        "Property children",
    ),
    EndpointSpec("collections", "GET", "/ontologies/{ontology}/collections", "List collections"),
    EndpointSpec(
        "collections",
        "GET",
        "/ontologies/{ontology}/collections/{collection_id}",
        "Collection item",
    ),
    EndpointSpec(
        "collections",
        "GET",
        "/ontologies/{ontology}/collections/{collection_id}/members",
        "Collection members",
    ),
    EndpointSpec("schemes", "GET", "/ontologies/{ontology}/schemes", "List schemes"),
    EndpointSpec("schemes", "GET", "/ontologies/{ontology}/schemes/{scheme_id}", "Scheme item"),
    EndpointSpec("mappings", "GET", "/mappings", "List mappings"),
    EndpointSpec("mappings", "POST", "/mappings", "Create mapping"),
    EndpointSpec("mappings", "GET", "/mappings/recent", "Recent mappings"),
    EndpointSpec("mappings", "GET/DELETE", "/mappings/{mapping_id}", "Mapping item"),
    EndpointSpec("mappings", "GET", "/mappings/statistics/ontologies", "Mapping stats by ontology"),
    EndpointSpec(
        "mappings",
        "GET",
        "/mappings/statistics/ontologies/{ontology}",
        "Mapping stats for ontology",
    ),
    EndpointSpec("mappings", "GET", "/ontologies/{ontology}/mappings", "Ontology mappings"),
    EndpointSpec(
        "mappings", "GET", "/ontologies/{ontology}/classes/{class_id}/mappings", "Class mappings"
    ),
    EndpointSpec("metrics", "GET", "/metrics", "List metrics"),
    EndpointSpec("metrics", "GET", "/metrics/missing", "Missing metrics"),
    EndpointSpec("metrics", "GET", "/ontologies/{ontology}/metrics", "Ontology metrics"),
    EndpointSpec(
        "metrics",
        "GET",
        "/ontologies/{ontology}/submissions/{submission_id}/metrics",
        "Submission metrics",
    ),
    EndpointSpec("notes", "GET/POST", "/notes", "List or create notes"),
    EndpointSpec("notes", "GET/PATCH/DELETE", "/notes/{note_id}", "Note item"),
    EndpointSpec("notes", "GET", "/ontologies/{ontology}/notes", "Ontology notes"),
    EndpointSpec("notes", "GET", "/ontologies/{ontology}/classes/{class_id}/notes", "Class notes"),
    EndpointSpec("replies", "GET/POST", "/replies", "List or create replies"),
    EndpointSpec("replies", "GET/PATCH/DELETE", "/replies/{reply_id}", "Reply item"),
    EndpointSpec("replies", "GET", "/notes/{note_id}/replies", "Note replies"),
    EndpointSpec("reviews", "GET/POST", "/reviews", "List or create reviews"),
    EndpointSpec("reviews", "GET/PATCH/DELETE", "/reviews/{review_id}", "Review item"),
    EndpointSpec("reviews", "GET", "/ontologies/{acronym}/reviews", "Ontology reviews"),
    EndpointSpec(
        "provisional_classes",
        "GET/POST",
        "/provisional_classes",
        "List or create provisional classes",
    ),
    EndpointSpec(
        "provisional_classes",
        "GET/PATCH/DELETE",
        "/provisional_classes/{provisional_class_id}",
        "Provisional class item",
    ),
    EndpointSpec(
        "provisional_classes",
        "GET",
        "/ontologies/{ontology}/provisional_classes",
        "Ontology provisional classes",
    ),
    EndpointSpec(
        "provisional_classes",
        "GET",
        "/users/{user}/provisional_classes",
        "User provisional classes",
    ),
    EndpointSpec(
        "provisional_relations",
        "GET/POST",
        "/provisional_relations",
        "List or create provisional relations",
    ),
    EndpointSpec(
        "provisional_relations",
        "GET/DELETE",
        "/provisional_relations/{provisional_relation_id}",
        "Provisional relation item",
    ),
    EndpointSpec("categories", "GET/POST", "/categories", "List or create categories"),
    EndpointSpec("categories", "GET/PUT/PATCH/DELETE", "/categories/{acronym}", "Category item"),
    EndpointSpec("categories", "GET", "/ontologies/{acronym}/categories", "Ontology categories"),
    EndpointSpec("groups", "GET/POST", "/groups", "List or create groups"),
    EndpointSpec("groups", "GET/PUT/PATCH/DELETE", "/groups/{acronym}", "Group item"),
    EndpointSpec("groups", "GET", "/ontologies/{acronym}/groups", "Ontology groups"),
    EndpointSpec("projects", "GET/POST", "/projects", "List or create projects"),
    EndpointSpec("projects", "GET/PUT/PATCH/DELETE", "/projects/{acronym}", "Project item"),
    EndpointSpec("projects", "GET", "/ontologies/{acronym}/projects", "Ontology projects"),
    EndpointSpec("slices", "GET/POST", "/slices", "List or create slices"),
    EndpointSpec("slices", "GET", "/slices/{slice_id}", "Slice item"),
    EndpointSpec("slices", "PATCH/DELETE", "/slices/{slice}", "Slice update/delete"),
    EndpointSpec("slices", "GET", "/slices/synchronize_groups", "Synchronize slice groups"),
    EndpointSpec("users", "GET/POST", "/users", "List or create users"),
    EndpointSpec("users", "GET/PUT/PATCH/DELETE", "/users/{username}", "User item"),
    EndpointSpec("users", "POST", "/users/authenticate", "Authenticate user"),
    EndpointSpec("users", "POST", "/users/create_reset_password_token", "Create reset token"),
    EndpointSpec("users", "POST", "/users/reset_password", "Reset password"),
)


WORKFLOW_SPECS: tuple[dict[str, str], ...] = (
    {
        "command": "workflows concept-resolve",
        "summary": "Resolve a concept by class ID or constrained search",
    },
    {
        "command": "workflows concept-expand",
        "summary": "Expand class neighborhood and hierarchy context",
    },
    {
        "command": "workflows concept-annotate-and-map",
        "summary": "Annotate text and enrich hits with mappings",
    },
    {
        "command": "workflows ontology-profile",
        "summary": "Aggregate ontology metadata, submission, metrics, analytics, and memberships",
    },
    {
        "command": "workflows ontology-compare",
        "summary": "Compare two ontologies using metrics, mappings, and probe coverage",
    },
    {
        "command": "workflows recommender-explain",
        "summary": "Run recommender with explicit weights and explanation context",
    },
    {
        "command": "workflows notes-thread-export",
        "summary": "Export notes and threaded replies in normalized form",
    },
    {
        "command": "workflows batch-classes-from-file",
        "summary": "Read class-ontology pairs from file and execute /batch",
    },
    {
        "command": "workflows fetch-all",
        "summary": "Traverse pagination for list endpoints and return all items",
    },
    {
        "command": "workflows pipeline-suggest-ontologies",
        "summary": "Recommend ontologies then preview search and annotation results",
    },
)
