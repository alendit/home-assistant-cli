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
