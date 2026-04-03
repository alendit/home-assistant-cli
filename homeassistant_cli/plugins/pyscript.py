"""Pyscript plugin for Home Assistant CLI (hass-cli)."""

from typing import Any, Dict, List, Optional

import click

import homeassistant_cli.autocompletion as autocompletion
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, load_json_input, to_attributes
import homeassistant_cli.remote as api

COLS = [
    ("SERVICE", "service"),
    ("NAME", "name"),
    ("DESCRIPTION", "description"),
]


def _load_service_data(
    arguments: Optional[str], json_input: Optional[str], json_file: Optional[str]
) -> Dict[str, Any]:
    """Load a pyscript service payload from key/value or JSON input."""
    if arguments and (json_input or json_file):
        raise click.UsageError("Specify either --arguments or --json/--json-file")

    if arguments:
        return to_attributes(arguments)

    payload = load_json_input(json_input, json_file)
    if not payload:
        return {}

    if not isinstance(payload, dict):
        raise click.UsageError("Service payload must be a JSON object")

    return payload


def _pyscript_services(
    ctx: Configuration, args: list[str], incomplete: str
) -> list[tuple[str, str]]:
    """Complete pyscript services by their short or fully-qualified name."""
    completions = autocompletion.services(ctx, args, incomplete)
    results: list[tuple[str, str]] = []
    for service, description in completions:
        if not service.startswith("pyscript."):
            continue
        short_name = service.split(".", 1)[1]
        if incomplete in short_name:
            results.append((short_name, description))
    return results


def _normalize_service_name(service: str) -> str:
    """Normalize a service name to the pyscript domain."""
    parts = service.split(".", 1)
    if len(parts) == 1:
        return service

    if parts[0] != "pyscript":
        raise click.UsageError("Pyscript service must be in the pyscript domain")

    return parts[1]


def _get_pyscript_services(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return pyscript services flattened into rows."""
    services = api.get_services(ctx)
    domain = next((item for item in services if item["domain"] == "pyscript"), None)
    if not domain:
        return []

    rows: List[Dict[str, Any]] = []
    for service, definition in domain["services"].items():
        row = {
            "domain": "pyscript",
            "service": service,
            **definition,
        }
        rows.append(row)

    return rows


@click.group("pyscript")
@pass_context
def cli(ctx: Configuration) -> None:
    """Work with pyscript services."""


@cli.command("list")
@pass_context
def list_cmd(ctx: Configuration) -> None:
    """List available pyscript services."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            _get_pyscript_services(ctx),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("reload")
@pass_context
def reload_cmd(ctx: Configuration) -> None:
    """Reload changed pyscript files."""
    ctx.auto_output("data")
    ctx.echo(format_output(ctx, api.call_service(ctx, "pyscript", "reload")))


@cli.command("stubs")
@pass_context
def stubs(ctx: Configuration) -> None:
    """Generate IDE stubs for pyscript."""
    ctx.auto_output("data")
    ctx.echo(format_output(ctx, api.call_service(ctx, "pyscript", "generate_stubs")))


@cli.command("call")
@click.argument("service", required=True, shell_complete=_pyscript_services)
@click.option(
    "--arguments", help="Comma separated key/value pairs to use as arguments."
)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def call(
    ctx: Configuration,
    service: str,
    arguments: Optional[str],
    json: Optional[str],
    json_file: Optional[str],
) -> None:
    """Call a pyscript service."""
    ctx.auto_output("data")
    ctx.echo(
        format_output(
            ctx,
            api.call_service(
                ctx,
                "pyscript",
                _normalize_service_name(service),
                _load_service_data(arguments, json, json_file),
            ),
        )
    )
