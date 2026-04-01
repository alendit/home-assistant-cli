"""Testing config-entry operations."""

import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli

CONFIG_ENTRIES = [
    {
        "entry_id": "entry-1",
        "domain": "codex_app_server",
        "title": "Codex App Server",
        "state": "loaded",
        "source": "user",
    },
    {
        "entry_id": "entry-2",
        "domain": "mqtt",
        "title": "MQTT",
        "state": "loaded",
        "source": "user",
    },
]


def test_config_entry_list() -> None:
    """List should return config entries."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entries",
        return_value=CONFIG_ENTRIES,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "config-entry", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["entry_id"] == "entry-1"


def test_config_entry_show() -> None:
    """Show should return one config entry by id."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entry",
        return_value=CONFIG_ENTRIES[0],
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "config-entry", "show", "entry-1"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["domain"] == "codex_app_server"
        assert payload["title"] == "Codex App Server"


def test_config_entry_show_with_data() -> None:
    """Show with data should include diagnostics when requested."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entry",
        return_value=CONFIG_ENTRIES[0],
    ):
        with mock.patch(
            "homeassistant_cli.remote.get_config_entry_diagnostics",
            return_value={"configured": {"bridge_url": "ws://127.0.0.1:4311"}},
        ) as get_diagnostics:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "config-entry", "show", "entry-1", "--with-data"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["config_entry"]["entry_id"] == "entry-1"
            assert payload["diagnostics"]["configured"]["bridge_url"] == (
                "ws://127.0.0.1:4311"
            )
            get_diagnostics.assert_called_once_with(mock.ANY, "entry-1")


def test_config_entry_handlers() -> None:
    """Handlers should return available flow handlers."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entry_flow_handlers",
        return_value=["codex_app_server", "mqtt"],
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "config-entry", "handlers"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert json.loads(result.output) == [
            {"handler": "codex_app_server"},
            {"handler": "mqtt"},
        ]


def test_config_entry_continue() -> None:
    """Continue should submit the JSON payload."""
    with mock.patch(
        "homeassistant_cli.remote.continue_config_entry_flow",
        return_value={"type": "create_entry", "result": {"title": "Codex"}},
    ) as continue_flow:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "config-entry",
                "continue",
                "flow-1",
                "--json",
                '{"bridge_url":"ws://127.0.0.1:4311"}',
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        continue_flow.assert_called_once_with(
            mock.ANY,
            "flow-1",
            {"bridge_url": "ws://127.0.0.1:4311"},
        )


def test_config_entry_create_submits_first_form() -> None:
    """Create should init the flow and submit the first payload."""
    with mock.patch(
        "homeassistant_cli.remote.init_config_entry_flow",
        return_value={"type": "form", "flow_id": "flow-1"},
    ) as init_flow:
        with mock.patch(
            "homeassistant_cli.remote.continue_config_entry_flow",
            return_value={"type": "create_entry", "result": {"title": "Codex"}},
        ) as continue_flow:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                [
                    "--output=json",
                    "config-entry",
                    "create",
                    "codex_app_server",
                    "--json",
                    '{"bridge_url":"ws://127.0.0.1:4311","default_model":"gpt-5.4"}',
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            init_flow.assert_called_once_with(mock.ANY, "codex_app_server", False)
            continue_flow.assert_called_once_with(
                mock.ANY,
                "flow-1",
                {
                    "bridge_url": "ws://127.0.0.1:4311",
                    "default_model": "gpt-5.4",
                },
            )


def test_config_entry_create_requires_payload_for_form() -> None:
    """Create should fail clearly when the first step is a form without payload."""
    with mock.patch(
        "homeassistant_cli.remote.init_config_entry_flow",
        return_value={"type": "form", "flow_id": "flow-1"},
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "config-entry", "create", "codex_app_server"],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        assert "Flow requires input" in result.output
