"""Config entry plugin for Home Assistant CLI (hass-cli)."""

from typing import Any, Dict, List, Optional, cast

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, load_json_input, raw_format_output
import homeassistant_cli.remote as api

COLS = [
    ("ENTRY_ID", "entry_id"),
    ("DOMAIN", "domain"),
    ("TITLE", "title"),
    ("STATE", "state"),
    ("SOURCE", "source"),
]

HANDLER_COLS = [("HANDLER", "handler")]


def _render_data(ctx: Configuration, data: Any) -> None:
    """Render a single data payload using the active output mode."""
    ctx.echo(
        raw_format_output(
            ctx.output,
            data,
            ctx.yaml(),
            no_headers=ctx.no_headers,
            table_format=ctx.table_format,
            sort_by=ctx.sort_by,
        )
    )


def _load_payload(json: Optional[str], json_file: Optional[str]) -> Dict[str, Any]:
    """Load a JSON object payload for flow operations."""
    payload = load_json_input(json, json_file)
    if not isinstance(payload, dict):
        raise click.UsageError("Flow payload must be a JSON object")

    return cast(Dict[str, Any], payload)


@click.group("config-entry")
@pass_context
def cli(ctx: Configuration) -> None:
    """Work with Home Assistant config entries and onboarding flows."""
    ctx.auto_output("table")


@cli.command("list")
@pass_context
def list_cmd(ctx: Configuration) -> None:
    """List config entries."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            api.get_config_entries(ctx),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("show")
@click.argument("entry_id", required=True)
@click.option(
    "--with-data",
    is_flag=True,
    default=False,
    help="Augment the config entry metadata with diagnostics data when available.",
)
@pass_context
def show(ctx: Configuration, entry_id: str, with_data: bool) -> None:
    """Show one config entry by id."""
    ctx.auto_output("data")
    entry = api.get_config_entry(ctx, entry_id)
    if entry is None:
        raise click.ClickException(f"Could not find config entry with id: {entry_id}")

    if not with_data:
        _render_data(ctx, entry)
        return

    _render_data(
        ctx,
        {
            "config_entry": entry,
            "diagnostics": api.get_config_entry_diagnostics(ctx, entry_id),
        },
    )


@cli.command("handlers")
@pass_context
def handlers(ctx: Configuration) -> None:
    """List available config-entry flow handlers."""
    ctx.auto_output("table")
    rows = [{"handler": handler} for handler in api.get_config_entry_flow_handlers(ctx)]
    ctx.echo(
        format_output(
            ctx,
            rows,
            columns=ctx.columns if ctx.columns else HANDLER_COLS,
        )
    )


@cli.command("init")
@click.argument("handler", required=True)
@click.option(
    "--show-advanced-options",
    is_flag=True,
    default=False,
    help="Request advanced options from the flow handler.",
)
@pass_context
def init(ctx: Configuration, handler: str, show_advanced_options: bool) -> None:
    """Start a config-entry flow."""
    ctx.auto_output("data")
    _render_data(
        ctx,
        api.init_config_entry_flow(ctx, handler, show_advanced_options),
    )


@cli.command("continue")
@click.argument("flow_id", required=True)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def continue_cmd(
    ctx: Configuration,
    flow_id: str,
    json: Optional[str],
    json_file: Optional[str],
) -> None:
    """Continue a config-entry flow."""
    ctx.auto_output("data")
    _render_data(
        ctx,
        api.continue_config_entry_flow(ctx, flow_id, _load_payload(json, json_file)),
    )


@cli.command("create")
@click.argument("handler", required=True)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--show-advanced-options",
    is_flag=True,
    default=False,
    help="Request advanced options from the flow handler.",
)
@pass_context
def create(
    ctx: Configuration,
    handler: str,
    json: Optional[str],
    json_file: Optional[str],
    show_advanced_options: bool,
) -> None:
    """Start a flow and submit the first form payload in one command."""
    ctx.auto_output("data")
    payload = _load_payload(json, json_file)
    result = api.init_config_entry_flow(ctx, handler, show_advanced_options)
    if result.get("type") != "form":
        _render_data(ctx, result)
        return

    if not payload:
        raise click.UsageError(
            "Flow requires input; provide --json/--json-file or use `config-entry continue`."
        )

    _render_data(
        ctx, api.continue_config_entry_flow(ctx, cast(str, result["flow_id"]), payload)
    )
