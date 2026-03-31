"""Tests for the dashboard plugin."""

import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_dashboard_show() -> None:
    """Dashboard show should return the named dashboard config."""
    config = {"views": [{"title": "Home"}]}
    with mock.patch(
        "homeassistant_cli.remote.lovelace_get_config", return_value=config
    ) as get_config:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "dashboard", "show", "dashboard-electricity"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        get_config.assert_called_once()
        data = json.loads(result.output)
        assert data["views"][0]["title"] == "Home"


def test_dashboard_save_from_json_file(tmp_path: Path) -> None:
    """Dashboard save should accept file-backed JSON payloads."""
    payload_path = tmp_path / "dashboard.json"
    payload_path.write_text(
        json.dumps(
            {
                "config": {"views": [{"title": "Office"}]},
                "url_path": "dashboard-electricity",
            }
        )
    )

    with mock.patch("homeassistant_cli.remote.lovelace_save_config") as save_config:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "dashboard",
                "save",
                "--json-file",
                str(payload_path),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        save_config.assert_called_once_with(
            mock.ANY,
            {"views": [{"title": "Office"}]},
            "dashboard-electricity",
        )
        data = json.loads(result.output)
        assert data["saved"] is True
        assert data["url_path"] == "dashboard-electricity"
