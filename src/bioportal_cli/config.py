from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://data.bioontology.org"
ENV_API_KEY = "BIOPORTAL_API_KEY"
ENV_BASE_URL = "BIOPORTAL_BASE_URL"
ENV_TIMEOUT = "BIOPORTAL_TIMEOUT"


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


def _xdg_config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def default_config_path() -> Path:
    return _xdg_config_home() / "bioportal-cli" / "config.json"


@dataclass(frozen=True)
class Config:
    api_key: str | None
    base_url: str
    timeout: float

    @staticmethod
    def from_sources(
        *,
        cli_api_key: str | None,
        cli_base_url: str | None,
        cli_timeout: float | None,
        config_path: Path | None = None,
    ) -> Config:
        path = config_path or default_config_path()
        file_data = _load_config_file(path)

        env_api_key = os.environ.get(ENV_API_KEY)
        env_base_url = os.environ.get(ENV_BASE_URL)
        env_timeout = os.environ.get(ENV_TIMEOUT)

        api_key = cli_api_key or env_api_key or _to_optional_str(file_data.get("api_key"))
        base_url = (
            cli_base_url
            or env_base_url
            or _to_optional_str(file_data.get("base_url"))
            or DEFAULT_BASE_URL
        )
        timeout_value = cli_timeout
        if timeout_value is None and env_timeout is not None:
            timeout_value = _parse_timeout(env_timeout)
        if timeout_value is None:
            timeout_value = _parse_timeout(file_data.get("timeout", 30.0))

        base_url = base_url.rstrip("/")
        if not base_url.startswith(("https://", "http://")):
            raise ConfigError("base URL must start with http:// or https://")

        if timeout_value <= 0:
            raise ConfigError("timeout must be greater than 0")

        return Config(api_key=api_key, base_url=base_url, timeout=timeout_value)


def write_config(*, api_key: str | None, base_url: str | None, timeout: float | None) -> Path:
    path = default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}
    if path.exists():
        data = _load_config_file(path)

    if api_key is not None:
        data["api_key"] = api_key
    if base_url is not None:
        data["base_url"] = base_url
    if timeout is not None:
        data["timeout"] = timeout

    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid config JSON at {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ConfigError(f"config file at {path} must be a JSON object")
    return parsed


def _to_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        return value
    raise ConfigError("string value expected in config")


def _parse_timeout(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ConfigError("timeout must be numeric") from exc
    raise ConfigError("timeout must be numeric")
