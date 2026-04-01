"""Tests for websocket-facing helpers."""

from unittest import mock

import homeassistant_cli.remote as remote
from homeassistant_cli.config import Configuration


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
        response.json.return_value = {"configured": {"bridge_url": "ws://127.0.0.1:4311"}}
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
