"""Tests for the history plugin."""

import json

from click.testing import CliRunner
import requests_mock

import homeassistant_cli.cli as cli

_HISTORY_URL = (
    "http://localhost:8123/api/history/period/2026-04-01T00%3A00%3A00%2B00%3A00"
    "?filter_entity_id=sensor.bedroom_temperature"
    "&end_time=2026-04-02T00%3A00%3A00%2B00%3A00"
)


def test_history_get_returns_flattened_events() -> None:
    """The history get command should flatten the per-entity payload."""
    payload = [
        [
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "20",
                "last_changed": "2026-04-01T00:00:00+00:00",
            },
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "21",
                "last_changed": "2026-04-01T12:00:00+00:00",
            },
        ]
    ]
    with requests_mock.Mocker() as mock:
        mock.get(_HISTORY_URL, json=payload, status_code=200)

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--server",
                "http://localhost:8123",
                "--output=json",
                "history",
                "get",
                "--since",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-02T00:00:00+00:00",
                "sensor.bedroom_temperature",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert json.loads(result.output) == payload[0]


def test_history_summary_returns_time_weighted_metrics() -> None:
    """Summary should compute a time-weighted average and ignore invalid states."""
    payload = [
        [
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "20",
                "last_changed": "2026-04-01T00:00:00+00:00",
            },
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "22",
                "last_changed": "2026-04-01T12:00:00+00:00",
            },
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "unknown",
                "last_changed": "2026-04-01T18:00:00+00:00",
            },
        ]
    ]
    with requests_mock.Mocker() as mock:
        mock.get(_HISTORY_URL, json=payload, status_code=200)

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--server",
                "http://localhost:8123",
                "--output=json",
                "history",
                "summary",
                "--since",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-02T00:00:00+00:00",
                "sensor.bedroom_temperature",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert json.loads(result.output) == [
            {
                "entity_id": "sensor.bedroom_temperature",
                "average": 20.667,
                "minimum": 20.0,
                "maximum": 22.0,
                "coverage_pct": 75.0,
                "coverage_hours": 18.0,
                "window_hours": 24.0,
                "valid_points": 2,
                "invalid_points": 1,
            }
        ]


def test_history_average_returns_average_focused_view() -> None:
    """Average should return a reduced summary view."""
    payload = [
        [
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "20",
                "last_changed": "2026-04-01T00:00:00+00:00",
            },
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "22",
                "last_changed": "2026-04-01T12:00:00+00:00",
            },
            {
                "entity_id": "sensor.bedroom_temperature",
                "state": "unknown",
                "last_changed": "2026-04-01T18:00:00+00:00",
            },
        ]
    ]
    with requests_mock.Mocker() as mock:
        mock.get(_HISTORY_URL, json=payload, status_code=200)

        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--server",
                "http://localhost:8123",
                "--output=json",
                "history",
                "average",
                "--since",
                "2026-04-01T00:00:00+00:00",
                "--end",
                "2026-04-02T00:00:00+00:00",
                "sensor.bedroom_temperature",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert json.loads(result.output) == [
            {
                "entity_id": "sensor.bedroom_temperature",
                "average": 20.667,
                "coverage_pct": 75.0,
                "coverage_hours": 18.0,
            }
        ]
