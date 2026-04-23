"""Tests for the public Python client."""

from typing import Any
from unittest import mock

import pytest
import requests_mock

from homeassistant_cli.exceptions import HomeAssistantCliError


def test_client_is_publicly_exported() -> None:
    """The package should expose HassClient at the top level."""
    from homeassistant_cli import HassClient

    assert HassClient is not None


def test_client_reads_same_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """The client should honor the same env defaults as the CLI."""
    from homeassistant_cli import HassClient

    monkeypatch.setenv("HASS_SERVER", "http://localhost:63333")
    monkeypatch.setenv("HASS_TOKEN", "supersecret")
    monkeypatch.setenv("HASS_PASSWORD", "legacy-secret")

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:63333/api/states/sensor.one",
            json={"entity_id": "sensor.one", "state": "on"},
            status_code=200,
        )

        client = HassClient()
        state = client.state.get("sensor.one")

        assert state == {"entity_id": "sensor.one", "state": "on"}
        assert mock_http.request_history[0].headers["Authorization"] == (
            "Bearer supersecret"
        )
        assert mock_http.request_history[0].headers["x-ha-access"] == "legacy-secret"


def test_client_prefers_hass_token_over_hassio_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HASS_TOKEN should win over HASSIO_TOKEN like the CLI."""
    from homeassistant_cli import HassClient

    monkeypatch.setenv("HASS_TOKEN", "winner")
    monkeypatch.setenv("HASSIO_TOKEN", "loser")

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8123/api/states/sensor.one",
            json={"entity_id": "sensor.one", "state": "on"},
            status_code=200,
        )

        client = HassClient()
        client.state.get("sensor.one")

        assert mock_http.request_history[0].headers["Authorization"] == "Bearer winner"


def test_client_explicit_args_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit constructor args should win over env defaults."""
    from homeassistant_cli import HassClient

    monkeypatch.setenv("HASS_SERVER", "http://localhost:63333")
    monkeypatch.setenv("HASS_TOKEN", "env-secret")

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8124/api/states/sensor.one",
            json={"entity_id": "sensor.one", "state": "off"},
            status_code=200,
        )

        client = HassClient(server="http://localhost:8124", token="explicit-secret")
        state = client.state.get("sensor.one")

        assert state is not None
        assert state["state"] == "off"
        assert mock_http.request_history[0].headers["Authorization"] == (
            "Bearer explicit-secret"
        )


def test_client_state_list_returns_structured_python_data(
    basic_entities,
) -> None:
    """State list should return Python objects, not formatted text."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8123/api/states",
            json=basic_entities,
            status_code=200,
        )

        client = HassClient()
        result = client.state.list(r"sensor\.(one|two)$")

        assert isinstance(result, list)
        assert {item["entity_id"] for item in result} == {"sensor.one", "sensor.two"}


def test_client_state_edit_is_non_interactive() -> None:
    """State edit should reject the CLI's editor-only mode."""
    from homeassistant_cli import HassClient

    client = HassClient()

    with pytest.raises(ValueError):
        client.state.edit("sensor.one")


def test_client_service_call_accepts_structured_payload() -> None:
    """Service calls should accept dictionaries directly."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        post = mock_http.post(
            "http://localhost:8123/api/services/light/turn_on",
            json=[{"entity_id": "light.kitchen"}],
            status_code=200,
        )

        client = HassClient()
        result = client.service.call(
            "light.turn_on",
            arguments={"entity_id": "light.kitchen", "brightness": 180},
        )

        assert result == [{"entity_id": "light.kitchen"}]
        assert post.request_history[0].json() == {
            "entity_id": "light.kitchen",
            "brightness": 180,
        }


def test_client_service_call_rejects_invalid_service_name() -> None:
    """Invalid service names should raise a Python exception, not exit."""
    from homeassistant_cli import HassClient

    client = HassClient()

    with pytest.raises(ValueError):
        client.service.call("not-a-service")


def test_client_raw_get_normalizes_api_methods() -> None:
    """Raw get should normalize bare API method names."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8123/api/config",
            json={"message": "success"},
            status_code=200,
        )

        client = HassClient()
        result = client.raw.get("config")

        assert result == {"message": "success"}


def test_client_raw_get_accepts_query_params() -> None:
    """Raw get should accept params without forcing them into the path string."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        matcher = mock_http.get(
            "http://localhost:8123/api/history/period/2026-04-19T18:00:00+00:00",
            json=[],
            status_code=200,
        )

        client = HassClient()
        result = client.raw.get(
            "/api/history/period/2026-04-19T18:00:00+00:00",
            params={
                "filter_entity_id": "sensor.power",
                "end_time": "2026-04-19T19:00:00+00:00",
            },
        )

        assert result == []
        assert matcher.call_count == 1
        query = mock_http.request_history[0].qs
        assert query["filter_entity_id"] == ["sensor.power"]
        assert query["end_time"][0].lower() == "2026-04-19t19:00:00+00:00"


def test_client_raw_ws_returns_structured_response() -> None:
    """Raw websocket calls should return the underlying response frame."""
    from homeassistant_cli import HassClient

    with mock.patch(
        "homeassistant_cli.remote.wsapi",
        return_value={"id": 1, "type": "result", "result": {"ok": True}},
    ) as wsapi:
        client = HassClient()
        result = client.raw.ws("config/wsmethod", json={"secret": "value"})

        assert result == {"id": 1, "type": "result", "result": {"ok": True}}
        wsapi.assert_called_once()


def test_client_raw_ws_rejects_non_object_payload() -> None:
    """Raw websocket payloads should be JSON objects."""
    from homeassistant_cli import HassClient

    client = HassClient()
    bad_payload: Any = ["wrong"]

    with pytest.raises(ValueError):
        client.raw.ws("config/wsmethod", json=bad_payload)


def test_client_dashboard_save_returns_normalized_payload() -> None:
    """Dashboard save should mirror the CLI's normalized success payload."""
    from homeassistant_cli import HassClient

    with mock.patch("homeassistant_cli.remote.lovelace_save_config") as save_config:
        client = HassClient()
        result = client.dashboard.save(
            {"views": [{"title": "Office"}]},
            url_path="dashboard-electricity",
        )

        assert result == {
            "saved": True,
            "url_path": "dashboard-electricity",
            "config": {"views": [{"title": "Office"}]},
        }
        save_config.assert_called_once_with(
            mock.ANY,
            {"views": [{"title": "Office"}]},
            "dashboard-electricity",
        )


def test_client_connection_options_propagate_to_session() -> None:
    """Connection options should reach the underlying requests session."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8123/api/states/sensor.one",
            json={"entity_id": "sensor.one", "state": "on"},
            status_code=200,
        )

        client = HassClient(
            timeout=17,
            insecure=True,
            cert="/tmp/client.pem",
            password="legacy-secret",
        )
        client.state.get("sensor.one")

        assert client._ctx.timeout == 17
        assert client._ctx.session is not None
        assert client._ctx.session.verify is False
        assert client._ctx.session.cert == "/tmp/client.pem"
        assert mock_http.request_history[0].headers["x-ha-access"] == "legacy-secret"


def test_client_state_get_returns_none_for_missing_entity() -> None:
    """Missing entities should return None, matching the lower-level API."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        mock_http.get(
            "http://localhost:8123/api/states/sensor.missing",
            text="Not found",
            status_code=404,
        )

        client = HassClient()

        assert client.state.get("sensor.missing") is None


def test_client_propagates_home_assistant_errors() -> None:
    """Low-level Home Assistant errors should remain Python exceptions."""
    from homeassistant_cli import HassClient

    with requests_mock.Mocker() as mock_http:
        mock_http.post(
            "http://localhost:8123/api/services/light/turn_on",
            text="boom",
            status_code=500,
        )

        client = HassClient()

        with pytest.raises(HomeAssistantCliError):
            client.service.call(
                "light.turn_on",
                arguments={"entity_id": "light.kitchen"},
            )
