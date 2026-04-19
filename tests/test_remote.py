"""Tests for websocket-facing helpers."""

from unittest import mock
import requests

import homeassistant_cli.remote as remote
from homeassistant_cli.config import Configuration
from homeassistant_cli.exceptions import HomeAssistantCliError


def test_wsapi_uses_asyncio_run() -> None:
    """Test websocket requests are dispatched via asyncio.run."""
    cfg = Configuration()

    def fake_run(coro):
        coro.close()
        return {"result": "worked"}

    with mock.patch("homeassistant_cli.remote.asyncio.run", fake_run):
        assert remote.wsapi(cfg, {"type": "config/test"}) == {"result": "worked"}


def test_get_entity_returns_result() -> None:
    """Test entity lookup returns the registry result payload."""
    cfg = Configuration()
    entity = {"entity_id": "sensor.one", "name": "One"}

    with mock.patch(
        "homeassistant_cli.remote.wsapi",
        return_value={"result": entity},
    ):
        assert remote.get_entity(cfg, "sensor.one") == entity


def test_get_todo_items_returns_result() -> None:
    """Test todo item listing returns the websocket result payload."""
    cfg = Configuration()
    items = [{"uid": "fb-1", "summary": "Wrong entity id used"}]

    with mock.patch(
        "homeassistant_cli.remote.wsapi",
        return_value={"result": {"items": items}},
    ) as wsapi:
        assert remote.get_todo_items(cfg, "todo.codex_feedback") == items
        wsapi.assert_called_once_with(
            cfg,
            {"type": "todo/item/list", "entity_id": "todo.codex_feedback"},
        )


def test_get_collection_item_config() -> None:
    """Test reading a collection config item over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"id": "auto-1", "alias": "Alpha"}
        restapi.return_value = response

        assert remote.get_collection_item_config(cfg, "automation", "auto-1") == {
            "id": "auto-1",
            "alias": "Alpha",
        }

        restapi.assert_called_once_with(
            cfg, remote.METH_GET, "/api/config/automation/config/auto-1"
        )


def test_get_states_falls_back_to_websocket_on_transport_error() -> None:
    """Bulk state listing should fall back to websocket when REST errors."""
    cfg = Configuration()
    states = [{"entity_id": "automation.alpha", "state": "on"}]

    with mock.patch(
        "homeassistant_cli.remote.restapi",
        side_effect=HomeAssistantCliError("Timeout talking to GET /api/states"),
    ) as restapi:
        with mock.patch(
            "homeassistant_cli.remote.wsapi",
            return_value={"result": states},
        ) as wsapi:
            assert remote.get_states(cfg) == states
            restapi.assert_called_once_with(
                cfg,
                remote.METH_GET,
                remote.hass.URL_API_STATES,
            )
            wsapi.assert_called_once_with(cfg, {"type": "get_states"})


def test_get_states_falls_back_to_websocket_on_rest_error_status() -> None:
    """Bulk state listing should fall back to websocket on non-200 REST status."""
    cfg = Configuration()
    states = [{"entity_id": "script.alpha", "state": "off"}]

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=500, text="boom")
        restapi.return_value = response
        with mock.patch(
            "homeassistant_cli.remote.wsapi",
            return_value={"result": states},
        ) as wsapi:
            assert remote.get_states(cfg) == states
            restapi.assert_called_once_with(
                cfg,
                remote.METH_GET,
                remote.hass.URL_API_STATES,
            )
            wsapi.assert_called_once_with(cfg, {"type": "get_states"})


def test_get_config_entries() -> None:
    """Test listing config entries over websocket."""
    cfg = Configuration()
    entries = [{"entry_id": "abc", "domain": "demo"}]

    with mock.patch(
        "homeassistant_cli.remote.wsapi",
        return_value={"result": entries},
    ) as wsapi:
        assert remote.get_config_entries(cfg) == entries
        wsapi.assert_called_once_with(cfg, {"type": "config_entries/get"})


def test_get_config_entry_flow_handlers() -> None:
    """Test reading flow handlers over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = ["codex_app_server", "mqtt"]
        restapi.return_value = response

        assert remote.get_config_entry_flow_handlers(cfg) == [
            "codex_app_server",
            "mqtt",
        ]
        restapi.assert_called_once_with(
            cfg, remote.METH_GET, "/api/config/config_entries/flow_handlers"
        )


def test_get_config_entry_diagnostics() -> None:
    """Test reading config-entry diagnostics over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {
            "configured": {"bridge_url": "ws://127.0.0.1:4311"}
        }
        restapi.return_value = response

        assert remote.get_config_entry_diagnostics(cfg, "entry-1") == {
            "configured": {"bridge_url": "ws://127.0.0.1:4311"}
        }
        restapi.assert_called_once_with(
            cfg,
            remote.METH_GET,
            "/api/diagnostics/config_entry/entry-1",
        )


def test_init_config_entry_flow() -> None:
    """Test starting a config-entry flow over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"type": "form", "flow_id": "flow-1"}
        restapi.return_value = response

        assert remote.init_config_entry_flow(cfg, "codex_app_server") == {
            "type": "form",
            "flow_id": "flow-1",
        }
        restapi.assert_called_once_with(
            cfg,
            remote.METH_POST,
            "/api/config/config_entries/flow",
            {
                "handler": "codex_app_server",
                "show_advanced_options": False,
            },
        )


def test_continue_config_entry_flow() -> None:
    """Test continuing a config-entry flow over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"
    payload = {"bridge_url": "ws://127.0.0.1:4311"}

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"type": "create_entry", "result": "ok"}
        restapi.return_value = response

        assert remote.continue_config_entry_flow(cfg, "flow-1", payload) == {
            "type": "create_entry",
            "result": "ok",
        }
        restapi.assert_called_once_with(
            cfg,
            remote.METH_POST,
            "/api/config/config_entries/flow/flow-1",
            payload,
        )


def test_update_collection_item_config() -> None:
    """Test updating a collection config item over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"
    payload = {"alias": "Updated Alpha"}

    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"result": "ok"}
        restapi.return_value = response

        assert remote.update_collection_item_config(
            cfg, "automation", "auto-1", payload
        ) == {"result": "ok"}

        restapi.assert_called_once_with(
            cfg,
            remote.METH_POST,
            "/api/config/automation/config/auto-1",
            payload,
        )


def test_restapi_timeout_mentions_retry_guidance() -> None:
    """Timeout errors should point operators at the global --timeout knob."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"
    cfg.timeout = 7

    with mock.patch(
        "requests.Session.request",
        side_effect=requests.exceptions.Timeout("too slow"),
    ):
        with mock.patch("homeassistant_cli.remote._LOGGER.exception"):
            try:
                remote.restapi(cfg, remote.METH_POST, "/api/conversation/process")
            except HomeAssistantCliError as ex:
                message = str(ex)
            else:
                raise AssertionError("Expected HomeAssistantCliError")

    assert "after 7s" in message
    assert "Retry with a larger --timeout value" in message
    assert "/api/conversation/process" in message
