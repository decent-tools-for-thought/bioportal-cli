from __future__ import annotations

import httpx

from bioportal_cli.client import BioPortalClient, BioPortalHTTPError


def test_client_get_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ontologies"
        return httpx.Response(200, json=[{"acronym": "NCIT"}])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://data.bioontology.org") as raw:
        client = BioPortalClient(
            base_url="https://data.bioontology.org",
            api_key="k",
            timeout=10,
            http_client=raw,
        )
        env = client.request("GET", "/ontologies")
        assert isinstance(env.data, list)
        assert env.data[0]["acronym"] == "NCIT"


def test_client_http_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid token"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://data.bioontology.org") as raw:
        client = BioPortalClient(
            base_url="https://data.bioontology.org",
            api_key="bad",
            timeout=10,
            http_client=raw,
        )
        try:
            client.request("GET", "/ontologies")
        except BioPortalHTTPError as exc:
            assert exc.status_code == 401
            assert "authentication failed" in exc.message
        else:
            raise AssertionError("expected BioPortalHTTPError")
