"""Tests for the pyscript CLI plugin."""

import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_pyscript_list() -> None:
    """List should return only pyscript services."""
    with mock.patch(
        "homeassistant_cli.remote.get_services",
        return_value=[
            {
                "domain": "light",
                "services": {
                    "turn_on": {
                        "name": "Turn on",
                        "description": "Turn on light",
                    }
                },
            },
            {
                "domain": "pyscript",
                "services": {
                    "reload": {
                        "name": "Reload pyscript",
                        "description": "Reload scripts",
                        "fields": {"global_ctx": {"required": False}},
                    },
                    "my_service": {
                        "name": "My Service",
                        "description": "Do something useful",
                        "fields": {"room": {"required": True}},
                    },
                },
            },
        ],
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "pyscript", "list"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert json.loads(result.output) == [
            {
                "domain": "pyscript",
                "service": "reload",
                "name": "Reload pyscript",
                "description": "Reload scripts",
                "fields": {"global_ctx": {"required": False}},
            },
            {
                "domain": "pyscript",
                "service": "my_service",
                "name": "My Service",
                "description": "Do something useful",
                "fields": {"room": {"required": True}},
            },
        ]


def test_pyscript_reload() -> None:
    """Reload should call the pyscript.reload service."""
    with mock.patch(
        "homeassistant_cli.remote.call_service",
        return_value=[{"result": "reloaded"}],
    ) as call_service:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "pyscript", "reload"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        call_service.assert_called_once_with(mock.ANY, "pyscript", "reload")
        assert json.loads(result.output) == [{"result": "reloaded"}]


def test_pyscript_stubs() -> None:
    """Stubs should call the pyscript.generate_stubs service."""
    with mock.patch(
        "homeassistant_cli.remote.call_service",
        return_value=[{"result": "generated"}],
    ) as call_service:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["--output=json", "pyscript", "stubs"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        call_service.assert_called_once_with(mock.ANY, "pyscript", "generate_stubs")
        assert json.loads(result.output) == [{"result": "generated"}]


def test_pyscript_call_with_arguments() -> None:
    """Call should submit shorthand key/value arguments to pyscript services."""
    with mock.patch(
        "homeassistant_cli.remote.call_service",
        return_value=[{"result": "done"}],
    ) as call_service:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "pyscript",
                "call",
                "run_task",
                "--arguments",
                "entity_id=light.kitchen,count=2",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        call_service.assert_called_once_with(
            mock.ANY,
            "pyscript",
            "run_task",
            {"entity_id": "light.kitchen", "count": "2"},
        )
        assert json.loads(result.output) == [{"result": "done"}]


def test_pyscript_call_accepts_fully_qualified_name() -> None:
    """Call should accept fully-qualified pyscript service names."""
    with mock.patch(
        "homeassistant_cli.remote.call_service",
        return_value=[{"result": "done"}],
    ) as call_service:
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "--output=json",
                "pyscript",
                "call",
                "pyscript.run_task",
                "--json",
                '{"name":"kitchen"}',
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        call_service.assert_called_once_with(
            mock.ANY,
            "pyscript",
            "run_task",
            {"name": "kitchen"},
        )


def test_pyscript_call_rejects_non_pyscript_domain() -> None:
    """Call should fail for services outside the pyscript domain."""
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["--output=json", "pyscript", "call", "light.turn_on"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "pyscript domain" in result.output


def test_pyscript_call_rejects_mixed_payload_options() -> None:
    """Call should reject mixed key/value and JSON payload input."""
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "--output=json",
            "pyscript",
            "call",
            "run_task",
            "--arguments",
            "entity_id=light.kitchen",
            "--json",
            '{"name":"kitchen"}',
        ],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "Specify either --arguments or --json/--json-file" in result.output
