"""Testing script operations."""
import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


SCRIPTS = [
    {
        "entity_id": "script.alpha",
        "state": "off",
        "attributes": {
            "friendly_name": "Alpha",
            "last_triggered": "2026-03-29T22:08:41+00:00",
        },
    },
    {
        "entity_id": "script.beta",
        "state": "off",
        "attributes": {"friendly_name": "Beta", "last_triggered": None},
    },
    {
        "entity_id": "automation.ignore_me",
        "state": "on",
        "attributes": {"friendly_name": "Ignore Me"},
    },
]


def test_script_list_filters_domain() -> None:
    """Only script entities should be listed."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCRIPTS):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "script", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2


def test_script_show_uses_slug() -> None:
    """Show should use the entity slug for config lookup."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCRIPTS):
        with mock.patch(
            'homeassistant_cli.remote.get_collection_item_config',
            return_value={"alias": "Alpha", "sequence": []},
        ) as get_config:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "script", "show", "Alpha"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload['entity_id'] == "script.alpha"
            get_config.assert_called_once_with(mock.ANY, 'script', 'alpha')


def test_script_update_uses_slug() -> None:
    """Update should target the script slug endpoint."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCRIPTS):
        with mock.patch(
            'homeassistant_cli.remote.update_collection_item_config',
            return_value={"result": "ok"},
        ) as update_config:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                [
                    "--output=json",
                    "script",
                    "update",
                    "script.alpha",
                    "--json",
                    '{"alias":"Updated Alpha"}',
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            update_config.assert_called_once_with(
                mock.ANY,
                'script',
                'alpha',
                {"alias": "Updated Alpha"},
            )


def test_script_run_passes_arguments() -> None:
    """Run should merge entity id with explicit arguments."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCRIPTS):
        with mock.patch(
            'homeassistant_cli.remote.call_service',
            return_value=[{"entity_id": "script.alpha", "state": "on"}],
        ) as call_service:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                [
                    "--output=json",
                    "script",
                    "run",
                    "script.alpha",
                    "--arguments",
                    "foo=bar",
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                'script',
                'turn_on',
                {'foo': 'bar', 'entity_id': 'script.alpha'},
            )


def test_script_stop() -> None:
    """Stop should call script.turn_off."""
    with mock.patch('homeassistant_cli.remote.get_states', return_value=SCRIPTS):
        with mock.patch(
            'homeassistant_cli.remote.call_service',
            return_value=[{"entity_id": "script.alpha", "state": "off"}],
        ) as call_service:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "script", "stop", "script.alpha"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                'script',
                'turn_off',
                {'entity_id': 'script.alpha'},
            )
