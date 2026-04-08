"""Tests for the logs CLI plugin."""

from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_logs_without_target_returns_full_log() -> None:
    """Logs should print the full error log when no target is given."""
    log_text = (
        "2026-04-04 10:00:00 ERROR [custom_components.pyscript] First error\n"
        "Traceback line 1\n"
        "2026-04-04 10:01:00 WARNING [homeassistant.components.telegram_bot] Second error\n"
    )
    with mock.patch(
        "homeassistant_cli.remote.get_raw_error_log", return_value=log_text
    ):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["logs"], catch_exceptions=False)

        assert result.exit_code == 0
        assert result.output == log_text + "\n"


def test_logs_filters_by_integration_and_keeps_traceback() -> None:
    """Filtering should keep full matching records, including traceback lines."""
    log_text = (
        "2026-04-04 10:00:00 ERROR [custom_components.pyscript] First error\n"
        "Traceback line 1\n"
        "Traceback line 2\n"
        "2026-04-04 10:01:00 WARNING [homeassistant.components.telegram_bot] Second error\n"
        "More telegram detail\n"
    )
    with mock.patch(
        "homeassistant_cli.remote.get_raw_error_log", return_value=log_text
    ):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["logs", "pyscript"], catch_exceptions=False)

        assert result.exit_code == 0
        assert result.output == (
            "2026-04-04 10:00:00 ERROR [custom_components.pyscript] First error\n"
            "Traceback line 1\n"
            "Traceback line 2\n"
        )


def test_logs_filters_by_component_alias() -> None:
    """Filtering should match Home Assistant component logger names."""
    log_text = (
        "2026-04-04 10:00:00 ERROR [custom_components.pyscript] First error\n"
        "2026-04-04 10:01:00 WARNING [homeassistant.components.telegram_bot] Second error\n"
    )
    with mock.patch(
        "homeassistant_cli.remote.get_raw_error_log", return_value=log_text
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli, ["logs", "telegram-bot"], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert result.output == (
            "2026-04-04 10:01:00 WARNING [homeassistant.components.telegram_bot] "
            "Second error\n"
        )


def test_logs_case_sensitive_flag() -> None:
    """Case-sensitive filtering should not match different casing."""
    log_text = "2026-04-04 10:00:00 ERROR [custom_components.pyscript] First error\n"
    with mock.patch(
        "homeassistant_cli.remote.get_raw_error_log", return_value=log_text
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            ["logs", "PYSCRIPT", "--case-sensitive"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert result.output == "\n"
