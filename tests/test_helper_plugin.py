"""Testing helper plugin operations."""

import json
from typing import Any
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli

STATES: list[dict[str, Any]] = [
    {
        "entity_id": "input_boolean.alpha",
        "state": "on",
        "attributes": {"friendly_name": "Alpha"},
    },
    {
        "entity_id": "timer.beta",
        "state": "idle",
        "attributes": {"friendly_name": "Beta"},
    },
    {
        "entity_id": "integration.gamma",
        "state": "1.23",
        "attributes": {"friendly_name": "Gamma"},
    },
    {
        "entity_id": "utility_meter.delta",
        "state": "4.56",
        "attributes": {"friendly_name": "Delta"},
    },
    {
        "entity_id": "scene.ignore_me",
        "state": "unknown",
        "attributes": {"friendly_name": "Ignore Me"},
    },
]


def _get_domain_states(_ctx: object, domain: str) -> list[dict[str, Any]]:
    return [state for state in STATES if state["entity_id"].startswith(f"{domain}.")]


def test_helper_list_aggregates_domains() -> None:
    """Helper list should aggregate supported helper domains."""
    with mock.patch(
        "homeassistant_cli.collection.get_domain_states",
        side_effect=_get_domain_states,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "helper", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 4
        assert data[0]["domain"] == "integration"
        assert data[1]["domain"] == "input_boolean"
        assert data[2]["domain"] == "timer"
        assert data[3]["domain"] == "utility_meter"


def test_helper_list_type_filter() -> None:
    """Helper type filter should narrow the domains queried."""
    with mock.patch(
        "homeassistant_cli.collection.get_domain_states",
        side_effect=_get_domain_states,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "helper", "list", "--type", "timer"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["entity_id"] == "timer.beta"


def test_helper_show() -> None:
    """Helper show should return the current entity payload."""
    with mock.patch(
        "homeassistant_cli.collection.get_domain_states",
        side_effect=_get_domain_states,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "helper", "show", "Alpha"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["entity_id"] == "input_boolean.alpha"


def test_helper_list_integration_type_filter() -> None:
    """Helper list should expose integration helpers."""
    with mock.patch(
        "homeassistant_cli.collection.get_domain_states",
        side_effect=_get_domain_states,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "helper", "list", "--type", "integration"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["entity_id"] == "integration.gamma"
