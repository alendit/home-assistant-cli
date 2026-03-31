"""Dashboard commands for Home Assistant CLI (hass-cli)."""

from typing import Any, Dict, Optional

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import load_json_input, raw_format_output
import homeassistant_cli.remote as api


def _show_data(ctx: Configuration, data: Dict[str, Any]) -> None:
    """Emit structured output."""
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


@click.group("dashboard")
@pass_context
def cli(ctx: Configuration) -> None:
    """Inspect and manage Lovelace dashboards."""
    ctx.auto_output("data")


@cli.command("show")
@click.argument("url_path", required=False)
@pass_context
def show(ctx: Configuration, url_path: Optional[str]) -> None:
    """Show the default or named dashboard config."""
    _show_data(ctx, api.lovelace_get_config(ctx, url_path))


@cli.command("save")
@click.argument("url_path", required=False)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def save(
    ctx: Configuration,
    url_path: Optional[str],
    json: Optional[str],
    json_file: Optional[str],
) -> None:
    """Replace the default or named dashboard config."""
    payload = load_json_input(json, json_file)
    if not isinstance(payload, dict):
        raise click.UsageError("Dashboard config must be a JSON object")

    config = payload.get("config", payload)
    if not isinstance(config, dict):
        raise click.UsageError("Dashboard config must be a JSON object")

    effective_url_path = url_path or payload.get("url_path")
    api.lovelace_save_config(ctx, config, effective_url_path)
    _show_data(
        ctx,
        {
            "saved": True,
            "url_path": effective_url_path,
            "config": config,
        },
    )
