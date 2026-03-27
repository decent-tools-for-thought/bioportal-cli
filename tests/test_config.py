from __future__ import annotations

import json

from bioportal_cli.config import Config, default_config_path


def test_config_precedence(monkeypatch: object, tmp_path: object) -> None:
    config_dir = tmp_path / "cfg"  # type: ignore[operator]
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))  # type: ignore[attr-defined]
    path = default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "api_key": "file-key",
                "base_url": "https://example.org",
                "timeout": 10,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("BIOPORTAL_API_KEY", "env-key")  # type: ignore[attr-defined]
    cfg = Config.from_sources(cli_api_key="cli-key", cli_base_url=None, cli_timeout=None)
    assert cfg.api_key == "cli-key"
    assert cfg.base_url == "https://example.org"
    assert cfg.timeout == 10


def test_invalid_timeout_rejected() -> None:
    try:
        Config.from_sources(
            cli_api_key=None,
            cli_base_url="https://data.bioontology.org",
            cli_timeout=0,
        )
    except ValueError as exc:
        assert "timeout" in str(exc)
    else:
        raise AssertionError("expected timeout validation error")
