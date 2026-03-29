"""Scene plugin for Home Assistant CLI (hass-cli)."""

import logging
import sys
from typing import Any, Dict, List

import click

import homeassistant_cli.collection as collection
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, raw_format_output
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)

COLS = [
    ("ENTITY", "entity_id"),
    ("NAME", "attributes.friendly_name"),
    ("STATE", "state"),
]


@click.group("scene")
@pass_context
def cli(ctx: Configuration) -> None:
    """Work with scenes from Home Assistant."""
    ctx.auto_output("table")


def _scenes(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return scene states only."""
    return collection.get_domain_states(ctx, "scene")


def _resolve(ctx: Configuration, ref: str) -> Dict[str, Any]:
    """Resolve a scene ref."""
    try:
        item = collection.resolve_item(_scenes(ctx), ref)
    except ValueError as ex:
        _LOGGING.error(str(ex))
        sys.exit(1)

    if not item:
        _LOGGING.error("Could not find scene with ref: %s", ref)
        sys.exit(1)

    return item


@cli.command("list")
@click.argument("scenefilter", default=".*", required=False)
@pass_context
def list_cmd(ctx: Configuration, scenefilter: str) -> None:
    """List scenes."""
    ctx.auto_output("table")
    items = _scenes(ctx)
    result = (
        items if scenefilter == ".*" else collection.filter_items(items, scenefilter)
    )
    ctx.echo(format_output(ctx, result, columns=ctx.columns if ctx.columns else COLS))


@cli.command("find")
@click.argument("pattern", required=True)
@pass_context
def find_cmd(ctx: Configuration, pattern: str) -> None:
    """Find scenes by regex."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            collection.filter_items(_scenes(ctx), pattern),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("show")
@click.argument("ref", required=True)
@pass_context
def show(ctx: Configuration, ref: str) -> None:
    """Show the current scene entity state."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    ctx.echo(
        raw_format_output(
            ctx.output,
            item,
            ctx.yaml(),
            no_headers=ctx.no_headers,
            table_format=ctx.table_format,
            sort_by=ctx.sort_by,
        )
    )


@cli.command("activate")
@click.argument("ref", required=True)
@click.option("--transition", type=float, default=None)
@pass_context
def activate(ctx: Configuration, ref: str, transition: float | None) -> None:
    """Activate a scene."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    data = {"entity_id": item["entity_id"]}
    if transition is not None:
        data["transition"] = transition
    ctx.echo(format_output(ctx, api.call_service(ctx, "scene", "turn_on", data)))
