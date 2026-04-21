"""Tests file for Home Assistant CLI (hass-cli)."""

import json

from click.testing import CliRunner
import requests_mock

import homeassistant_cli.autocompletion as autocompletion
import homeassistant_cli.cli as cli
from homeassistant_cli.config import Configuration


def test_service_list(default_services) -> None:
    """Test services can be listed."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/services",
            json=default_services,
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "service", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 12


def test_service_filter(default_services) -> None:
    """Test services can be listed."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/services",
            json=default_services,
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "service", "list", "homeassistant\\..*config.*"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2


def test_service_completion(default_services) -> None:
    """Test completion for services with filter."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://localhost:8123/api/services",
            json=default_services,
            status_code=200,
        )

        cfg = Configuration()

        result = autocompletion.services(cfg, ["service", "call"], "light.turn")
        assert len(result) == 2

        resultdict = dict(result)

        assert "light.turn_on" in resultdict
        assert "light.turn_off" in resultdict


def test_service_call(default_services) -> None:
    """Test basic call of a service."""
    with requests_mock.Mocker() as mock:

        post = mock.post(
            "http://localhost:8123/api/services/homeassistant/restart",
            json={"result": "bogus"},
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "service", "call", "homeassistant.restart"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        assert post.call_count == 1


def test_service_call_with_json_payload(default_services) -> None:
    """Call should accept structured payloads as JSON."""
    with requests_mock.Mocker() as mock:
        post = mock.post(
            "http://localhost:8123/api/services/light/turn_on",
            json={"result": "ok"},
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "service",
                "call",
                "light.turn_on",
                "--json",
                '{"entity_id":"light.kitchen","brightness":180}',
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert post.call_count == 1
        assert post.request_history[0].json() == {
            "entity_id": "light.kitchen",
            "brightness": 180,
        }


def test_service_call_accepts_multi_entity_arguments(default_services) -> None:
    """Call should preserve multi-value shorthand arguments as lists."""
    with requests_mock.Mocker() as mock:
        post = mock.post(
            "http://localhost:8123/api/services/light/turn_on",
            json={"result": "ok"},
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "service",
                "call",
                "light.turn_on",
                "--arguments",
                "entity_id=light.kitchen,light.living_room",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert post.call_count == 1
        assert post.request_history[0].json() == {
            "entity_id": ["light.kitchen", "light.living_room"]
        }


def test_service_call_rejects_mixed_payload_modes(default_services) -> None:
    """Call should reject mixed shorthand and JSON payloads."""
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "--output=json",
            "service",
            "call",
            "light.turn_on",
            "--arguments",
            "entity_id=light.kitchen",
            "--json",
            '{"brightness":180}',
        ],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "Specify either --arguments or --json/--json-file" in result.output


def test_service_call_rejects_malformed_arguments(default_services) -> None:
    """Call should surface a usage error for invalid shorthand input."""
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "--output=json",
            "service",
            "call",
            "light.turn_on",
            "--arguments",
            "light.kitchen",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "Arguments must be comma-separated key=value pairs." in result.output
    assert "Example: entity_id=light.kitchen" in result.output
    assert "Use --json" in result.output


def test_service_call_return_response(default_services) -> None:
    """Test service call can request response payloads."""
    with requests_mock.Mocker() as mock:
        post = mock.post(
            "http://localhost:8123/api/services/homeassistant/restart"
            "?return_response=true",
            json=[{"entity_id": "sensor.foo"}],
            status_code=200,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "service",
                "call",
                "--return-response",
                "homeassistant.restart",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        assert post.call_count == 1
