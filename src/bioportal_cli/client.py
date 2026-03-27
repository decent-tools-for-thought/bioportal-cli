from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class BioPortalError(RuntimeError):
    """Base exception for BioPortal client errors."""


class BioPortalHTTPError(BioPortalError):
    def __init__(self, status_code: int, message: str, payload: Any | None = None) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.payload = payload


class BioPortalNetworkError(BioPortalError):
    pass


@dataclass(frozen=True)
class ResponseEnvelope:
    status_code: int
    headers: dict[str, str]
    data: Any


class BioPortalClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        timeout: float,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._external_client = http_client
        self._client = http_client or httpx.Client(base_url=self._base_url, timeout=timeout)

    def close(self) -> None:
        if self._external_client is None:
            self._client.close()

    def __enter__(self) -> BioPortalClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> ResponseEnvelope:
        req_headers = dict(headers or {})
        if self._api_key:
            req_headers["Authorization"] = f"apikey token={self._api_key}"

        safe_params = self._clean_params(params)

        try:
            response = self._client.request(
                method=method,
                url=path,
                params=safe_params,
                json=json_body,
                headers=req_headers,
            )
        except httpx.TimeoutException as exc:
            raise BioPortalNetworkError(f"request timed out after {self._timeout} seconds") from exc
        except httpx.RequestError as exc:
            raise BioPortalNetworkError(f"network error: {exc}") from exc

        return self._to_envelope(response)

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        req_headers = dict(headers or {})
        if self._api_key:
            req_headers["Authorization"] = f"apikey token={self._api_key}"
        safe_params = self._clean_params(params)

        try:
            response = self._client.request(
                method=method, url=path, params=safe_params, headers=req_headers
            )
        except httpx.TimeoutException as exc:
            raise BioPortalNetworkError(f"request timed out after {self._timeout} seconds") from exc
        except httpx.RequestError as exc:
            raise BioPortalNetworkError(f"network error: {exc}") from exc

        if response.status_code >= 400:
            raise self._to_http_error(response)
        return response.text

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        req_headers = dict(headers or {})
        if self._api_key:
            req_headers["Authorization"] = f"apikey token={self._api_key}"
        safe_params = self._clean_params(params)
        try:
            response = self._client.request(
                method=method, url=path, params=safe_params, headers=req_headers
            )
        except httpx.TimeoutException as exc:
            raise BioPortalNetworkError(f"request timed out after {self._timeout} seconds") from exc
        except httpx.RequestError as exc:
            raise BioPortalNetworkError(f"network error: {exc}") from exc
        if response.status_code >= 400:
            raise self._to_http_error(response)
        return response.content

    def paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int | None = None,
    ) -> list[Any]:
        collected: list[Any] = []
        page = 1
        fetched = 0
        while True:
            next_params = dict(params or {})
            if "page" not in next_params:
                next_params["page"] = page
            envelope = self.request("GET", path, params=next_params)
            data = envelope.data
            if isinstance(data, list):
                collected.extend(data)
                if len(data) == 0:
                    break
                page += 1
                fetched += 1
                if max_pages is not None and fetched >= max_pages:
                    break
                continue
            if isinstance(data, dict):
                # When API returns an object, return single payload and stop.
                collected.append(data)
                break
            break
        return collected

    def _to_envelope(self, response: httpx.Response) -> ResponseEnvelope:
        if response.status_code >= 400:
            raise self._to_http_error(response)
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise BioPortalError("malformed JSON response from server") from exc
        else:
            text = response.text
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = text
        return ResponseEnvelope(
            status_code=response.status_code,
            headers=dict(response.headers),
            data=data,
        )

    def _to_http_error(self, response: httpx.Response) -> BioPortalHTTPError:
        detail: Any | None = None
        message = response.reason_phrase
        try:
            detail = response.json()
            if isinstance(detail, dict):
                possible = detail.get("error") or detail.get("message")
                if isinstance(possible, str):
                    message = possible
            elif isinstance(detail, str):
                message = detail
        except json.JSONDecodeError:
            if response.text.strip():
                message = response.text.strip()

        if response.status_code == 401:
            message = f"authentication failed: {message}"
        if response.status_code == 429:
            message = f"rate limit exceeded: {message}"
        return BioPortalHTTPError(response.status_code, message, payload=detail)

    @staticmethod
    def _clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
        if params is None:
            return {}
        clean: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                clean[key] = "true" if value else "false"
                continue
            if isinstance(value, (list, tuple, set)):
                clean[key] = ",".join(str(v) for v in value)
                continue
            clean[key] = value
        return clean

    @staticmethod
    def encode_identifier(value: str) -> str:
        return quote(value, safe="")

    @staticmethod
    def comma_or_iter(value: str | Iterable[str] | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return ",".join(value)
