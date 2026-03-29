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

    with mock.patch('homeassistant_cli.remote.asyncio.run', fake_run):
        assert remote.wsapi(cfg, {"type": "config/test"}) == {
            "result": "worked"
        }


def test_get_entity_returns_result() -> None:
    """Test entity lookup returns the registry result payload."""
    cfg = Configuration()
    entity = {"entity_id": "sensor.one", "name": "One"}

    with mock.patch(
        'homeassistant_cli.remote.wsapi',
        return_value={"result": entity},
    ):
        assert remote.get_entity(cfg, "sensor.one") == entity


def test_get_collection_item_config() -> None:
    """Test reading a collection config item over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"

    with mock.patch('homeassistant_cli.remote.restapi') as restapi:
        response = mock.Mock(status_code=200)
        response.json.return_value = {"id": "auto-1", "alias": "Alpha"}
        restapi.return_value = response

        assert remote.get_collection_item_config(
            cfg, "automation", "auto-1"
        ) == {"id": "auto-1", "alias": "Alpha"}

        restapi.assert_called_once_with(
            cfg, remote.METH_GET, "/api/config/automation/config/auto-1"
        )


def test_update_collection_item_config() -> None:
    """Test updating a collection config item over REST."""
    cfg = Configuration()
    cfg.server = "http://localhost:8123"
    payload = {"alias": "Updated Alpha"}

    with mock.patch('homeassistant_cli.remote.restapi') as restapi:
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
