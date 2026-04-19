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
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "script", "list"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2


def test_script_list_falls_back_when_bulk_state_rest_call_fails() -> None:
    """List should still work when /api/states falls back to websocket."""
    with mock.patch("homeassistant_cli.remote.restapi") as restapi:
        response = mock.Mock(status_code=500, text="boom")
        restapi.return_value = response
        with mock.patch(
            "homeassistant_cli.remote.wsapi",
            return_value={"result": SCRIPTS},
        ) as wsapi:
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "script", "list"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert [item["entity_id"] for item in data] == [
                "script.alpha",
                "script.beta",
            ]
            restapi.assert_called_once()
            wsapi.assert_called_once_with(mock.ANY, {"type": "get_states"})


def test_script_show_uses_slug() -> None:
    """Show should use the entity slug for config lookup."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.get_collection_item_config",
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
            assert payload["entity_id"] == "script.alpha"
            get_config.assert_called_once_with(mock.ANY, "script", "alpha")


def test_script_export_returns_stored_payload() -> None:
    """Export should return only the stored script config."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.get_collection_item_config",
            return_value={"alias": "Alpha", "sequence": []},
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli.cli,
                ["--output=json", "script", "export", "Alpha"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload == {"alias": "Alpha", "sequence": []}


def test_script_export_uses_direct_entity_lookup() -> None:
    """Export should resolve exact entity ids without listing all states."""
    with mock.patch(
        "homeassistant_cli.remote.get_state",
        return_value=SCRIPTS[0],
    ) as get_state:
        with mock.patch(
            "homeassistant_cli.remote.get_states",
            side_effect=AssertionError("get_states should not be used"),
        ):
            with mock.patch(
                "homeassistant_cli.remote.get_collection_item_config",
                return_value={"alias": "Alpha", "sequence": []},
            ):
                runner = CliRunner()
                result = runner.invoke(
                    cli.cli,
                    ["--output=json", "script", "export", "script.alpha"],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0
                payload = json.loads(result.output)
                assert payload == {"alias": "Alpha", "sequence": []}
                get_state.assert_not_called()


def test_script_update_uses_slug() -> None:
    """Update should target the script slug endpoint."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.update_collection_item_config",
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
                "script",
                "alpha",
                {"alias": "Updated Alpha"},
            )


def test_script_patch_merges_stored_payload() -> None:
    """Patch should merge onto the stored script config."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.get_collection_item_config",
            return_value={
                "alias": "Alpha",
                "mode": "single",
                "fields": {"room": "bedroom", "scene": "night"},
            },
        ):
            with mock.patch(
                "homeassistant_cli.remote.update_collection_item_config",
                return_value={"result": "ok"},
            ) as update_config:
                runner = CliRunner()
                result = runner.invoke(
                    cli.cli,
                    [
                        "--output=json",
                        "script",
                        "patch",
                        "script.alpha",
                        "--json",
                        '{"mode":"queued","fields":{"scene":"evening"}}',
                    ],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0
                update_config.assert_called_once_with(
                    mock.ANY,
                    "script",
                    "alpha",
                    {
                        "alias": "Alpha",
                        "mode": "queued",
                        "fields": {"room": "bedroom", "scene": "evening"},
                    },
                )


def test_script_run_passes_arguments() -> None:
    """Run should merge entity id with explicit arguments."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.call_service",
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
                "script",
                "turn_on",
                {"foo": "bar", "entity_id": "script.alpha"},
            )


def test_script_run_accepts_json_payload() -> None:
    """Run should accept structured JSON payloads."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.call_service",
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
                    "--json",
                    '{"foo":"bar","nested":{"scene":"evening"}}',
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                "script",
                "turn_on",
                {
                    "foo": "bar",
                    "nested": {"scene": "evening"},
                    "entity_id": "script.alpha",
                },
            )


def test_script_run_accepts_json_file(tmp_path) -> None:
    """Run should accept structured JSON payloads from a file."""
    payload = tmp_path / "script.json"
    payload.write_text('{"foo":"bar","nested":{"scene":"evening"}}')

    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.call_service",
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
                    "--json-file",
                    str(payload),
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            call_service.assert_called_once_with(
                mock.ANY,
                "script",
                "turn_on",
                {
                    "foo": "bar",
                    "nested": {"scene": "evening"},
                    "entity_id": "script.alpha",
                },
            )


def test_script_run_rejects_mixed_payload_modes() -> None:
    """Run should reject mixed shorthand and JSON payloads."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
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
                "--json",
                '{"nested":{"scene":"evening"}}',
            ],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        assert "Specify either --arguments or --json/--json-file" in result.output


def test_script_stop() -> None:
    """Stop should call script.turn_off."""
    with mock.patch("homeassistant_cli.remote.get_states", return_value=SCRIPTS):
        with mock.patch(
            "homeassistant_cli.remote.call_service",
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
                "script",
                "turn_off",
                {"entity_id": "script.alpha"},
            )
