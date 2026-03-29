"""Testing automation operations."""
import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


AUTOMATIONS = [
    {
        "entity_id": "automation.alpha",
        "state": "on",
        "attributes": {
            "friendly_name": "Alpha",
            "id": "auto-1",
            "last_triggered": "2026-03-29T22:08:41+00:00",
        },
    },
    {
        "entity_id": "automation.beta",
        "state": "off",
        "attributes": {
            "friendly_name": "Beta",
            "id": "auto-2",
            "last_triggered": None,
        },
    },
    {
        "entity_id": "scene.ignore_me",
        "state": "unknown",
        "attributes": {"friendly_name": "Ignore Me"},
    },
]


def test_automation_list_filters_domain() -> None:
    """Only automation entities should be listed."""
    with mock.patch(
        'homeassistant_cli.remote.get_states', return_value=AUTOMATIONS
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "automation", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]['entity_id'] == "automation.alpha"
        assert data[1]['entity_id'] == "automation.beta"


def test_automation_find_matches_name() -> None:
    """Find should match friendly names."""
    with mock.patch(
        'homeassistant_cli.remote.get_states', return_value=AUTOMATIONS
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "automation", "find", "Bet"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['entity_id'] == "automation.beta"


def test_automation_show_by_id() -> None:
    """Show should resolve via automation config id."""
    with mock.patch(
        'homeassistant_cli.remote.get_states', return_value=AUTOMATIONS
    ):
        with mock.patch(
            'homeassistant_cli.remote.get_collection_item_config',
            return_value={"id": "auto-1", "alias": "Alpha"},
        ) as get_config:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "automation", "show", "auto-1"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload['id'] == "auto-1"
            assert payload['entity_id'] == "automation.alpha"
            assert payload['friendly_name'] == "Alpha"
            get_config.assert_called_once()


def test_automation_update_by_alias() -> None:
    """Update should resolve by alias and use the storage id."""
    with mock.patch(
        'homeassistant_cli.remote.get_states', return_value=AUTOMATIONS
    ):
        with mock.patch(
            'homeassistant_cli.remote.update_collection_item_config',
            return_value={"result": "ok"},
        ) as update_config:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                [
                    "--output=json",
                    "automation",
                    "update",
                    "Alpha",
                    "--json",
                    '{"alias":"Updated Alpha"}',
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            update_config.assert_called_once_with(
                mock.ANY,
                'automation',
                'auto-1',
                {"alias": "Updated Alpha"},
            )


def test_automation_trigger() -> None:
    """Trigger should call the automation service with the entity id."""
    with mock.patch(
        'homeassistant_cli.remote.get_states', return_value=AUTOMATIONS
    ):
        with mock.patch(
            'homeassistant_cli.remote.call_service',
            return_value=[{"entity_id": "automation.alpha", "state": "on"}],
        ) as call_service:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "automation", "trigger", "automation.alpha"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                'automation',
                'trigger',
                {'entity_id': 'automation.alpha'},
            )
