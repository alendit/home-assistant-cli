"""Tests for the info command."""

import json

from click.testing import CliRunner
import requests_mock

import homeassistant_cli.cli as cli
from homeassistant_cli.exceptions import HomeAssistantCliError
import homeassistant_cli.yaml as yaml

VALID_INFO = {
    "base_url": "http://localhost:8123",
    "location_name": "Home",
    "requires_api_password": False,
    "version": "2026.3.1",
}

CONFIG_RESPONSE = {
    "location_name": "Home",
    "version": "2026.3.1",
}


def test_info_without_server_running() -> None:
    """Test proper failure when server not running."""
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--server", "http://donotexist.inf", "info"])
    assert result.exit_code == 1
    assert isinstance(result.exception, HomeAssistantCliError)
    assert (
        str(result.exception) == "Unexpected error getting configuration: "
        "Error connecting to http://donotexist.inf/api/config"
    )


def test_info_json() -> None:
    """Test info reads properly with JSON."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/config",
            json=CONFIG_RESPONSE,
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--server", "http://localhost:8123", "--output=json", "info"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert [VALID_INFO] == json.loads(result.output)


def test_info_unauth() -> None:
    """Test info handles auth failures."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/config",
            json={},
            status_code=401,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--server", "http://localhost:8123", "--output=json", "info"],
            catch_exceptions=True,
        )
        assert result.exit_code != 0
        assert isinstance(result.exception, HomeAssistantCliError)
        assert str(result.exception) == "Error while getting all configuration: {}"


def test_info_yaml() -> None:
    """Test info reads properly with YAML."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/config",
            json=CONFIG_RESPONSE,
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--server", "http://localhost:8123", "--output=yaml", "info"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert [VALID_INFO] == yaml.loadyaml(yaml.yaml(), result.output)
