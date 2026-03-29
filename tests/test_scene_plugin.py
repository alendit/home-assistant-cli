"""Testing scene operations."""
import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


SCENES = [
    {
        "entity_id": "scene.alpha",
        "state": "unknown",
        "attributes": {"friendly_name": "Alpha"},
    },
    {
        "entity_id": "scene.beta",
        "state": "unknown",
        "attributes": {"friendly_name": "Beta"},
    },
    {
        "entity_id": "script.ignore_me",
        "state": "off",
        "attributes": {"friendly_name": "Ignore Me"},
    },
]


def test_scene_list_filters_domain() -> None:
    """Only scene entities should be listed."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCENES):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "scene", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2


def test_scene_show() -> None:
    """Show should return the current scene entity payload."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCENES):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "scene", "show", "Alpha"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload['entity_id'] == "scene.alpha"


def test_scene_activate() -> None:
    """Activate should call scene.turn_on with the entity id."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCENES):
        with mock.patch(
            'homeassistant_cli.remote.call_service',
            return_value=[{"entity_id": "scene.alpha", "state": "scening"}],
        ) as call_service:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "scene", "activate", "scene.alpha"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                'scene',
                'turn_on',
                {'entity_id': 'scene.alpha'},
            )
