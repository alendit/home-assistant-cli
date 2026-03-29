"""Tests for Home Assistant OS/Supervisor commands."""
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_ha_info_uses_single_rest_call() -> None:
    """Test ha commands only issue one REST request per helper call."""
    response = mock.Mock()
    response.ok = True
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": {"status": "ok"}}

    with mock.patch(
        'homeassistant_cli.remote.restapi',
        return_value=response,
    ) as restapi:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "ha", "core", "info"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    restapi.assert_called_once()


def test_ha_update_uses_packaging_versions() -> None:
    """Test version comparisons still work for core updates."""
    response = mock.Mock()
    response.ok = True
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": {
            "version": "2026.3.1",
            "version_latest": "2026.3.1",
        }
    }

    with mock.patch(
        'homeassistant_cli.remote.restapi',
        return_value=response,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["ha", "core", "update"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert result.output == "Already running the latest release\n"
