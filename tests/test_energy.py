"""Tests for the energy plugin."""

import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_energy_show() -> None:
    """Energy show should return the current preferences."""
    prefs = {
        "energy_sources": [],
        "device_consumption": [{"stat_consumption": "sensor.alpha", "name": "Alpha"}],
        "device_consumption_water": [],
    }
    with mock.patch("homeassistant_cli.remote.energy_get_prefs", return_value=prefs):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "energy", "show"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["device_consumption"][0]["stat_consumption"] == "sensor.alpha"


def test_energy_device_add() -> None:
    """Energy device add should append a new device consumption entry."""
    prefs = {
        "energy_sources": [],
        "device_consumption": [{"stat_consumption": "sensor.alpha", "name": "Alpha"}],
        "device_consumption_water": [],
    }

    with (
        mock.patch("homeassistant_cli.remote.energy_get_prefs", return_value=prefs),
        mock.patch(
            "homeassistant_cli.remote.energy_save_prefs",
            side_effect=lambda _ctx, payload: payload,
        ) as save_prefs,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "energy",
                "device",
                "add",
                "sensor.beta",
                "--rate",
                "sensor.beta_power",
                "--name",
                "Beta",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        saved_payload = save_prefs.call_args[0][1]
        assert saved_payload["device_consumption"] == [
            {"stat_consumption": "sensor.alpha", "name": "Alpha"},
            {
                "stat_consumption": "sensor.beta",
                "stat_rate": "sensor.beta_power",
                "name": "Beta",
            },
        ]


def test_energy_grid_clear() -> None:
    """Energy grid clear should remove only grid sources."""
    prefs = {
        "energy_sources": [
            {"type": "grid", "stat_energy_from": "sensor.grid"},
            {"type": "solar", "stat_energy_from": "sensor.solar"},
        ],
        "device_consumption": [],
        "device_consumption_water": [],
    }

    with (
        mock.patch("homeassistant_cli.remote.energy_get_prefs", return_value=prefs),
        mock.patch(
            "homeassistant_cli.remote.energy_save_prefs",
            side_effect=lambda _ctx, payload: payload,
        ) as save_prefs,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "energy", "grid", "clear"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        saved_payload = save_prefs.call_args[0][1]
        assert saved_payload["energy_sources"] == [
            {"type": "solar", "stat_energy_from": "sensor.solar"}
        ]
