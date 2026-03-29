"""Script plugin for Home Assistant CLI (hass-cli)."""

import json as json_
import logging
import sys
from typing import Any, Dict, List, cast

import click

import homeassistant_cli.collection as collection
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import (
    format_output,
    raw_format_output,
    to_attributes,
)
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)

COLS = [
    ("ENTITY", "entity_id"),
    ("NAME", "attributes.friendly_name"),
    ("STATE", "state"),
    ("LAST_TRIGGERED", "attributes.last_triggered"),
]


@click.group("script")
@pass_context
def cli(ctx: Configuration) -> None:
    """Work with scripts from Home Assistant."""
    ctx.auto_output("table")


def _scripts(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return script states only."""
    return collection.get_domain_states(ctx, "script")


def _resolve(ctx: Configuration, ref: str) -> Dict[str, Any]:
    """Resolve a script ref."""
    try:
        item = collection.resolve_item(_scripts(ctx), ref)
    except ValueError as ex:
        _LOGGING.error(str(ex))
        sys.exit(1)

    if not item:
        _LOGGING.error("Could not find script with ref: %s", ref)
        sys.exit(1)

    return item


def _load_json(source: str) -> Dict[str, Any]:
    """Load JSON from option value or stdin."""
    return cast(
        Dict[str, Any],
        json_.loads(source if source != "-" else click.get_text_stream("stdin").read()),
    )


@cli.command("list")
@click.argument("scriptfilter", default=".*", required=False)
@pass_context
def list_cmd(ctx: Configuration, scriptfilter: str) -> None:
    """List scripts."""
    ctx.auto_output("table")
    items = _scripts(ctx)
    result = (
        items if scriptfilter == ".*" else collection.filter_items(items, scriptfilter)
    )
    ctx.echo(format_output(ctx, result, columns=ctx.columns if ctx.columns else COLS))


@cli.command("find")
@click.argument("pattern", required=True)
@pass_context
def find_cmd(ctx: Configuration, pattern: str) -> None:
    """Find scripts by regex."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            collection.filter_items(_scripts(ctx), pattern),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("show")
@click.argument("ref", required=True)
@pass_context
def show(ctx: Configuration, ref: str) -> None:
    """Show stored script configuration."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    payload = api.get_collection_item_config(
        ctx,
        "script",
        collection.entity_slug(item["entity_id"]),
    )
    payload = {
        "entity_id": item["entity_id"],
        "state": item["state"],
        "friendly_name": collection.get_item_name(item),
        **payload,
    }
    ctx.echo(
        raw_format_output(
            ctx.output,
            payload,
            ctx.yaml(),
            no_headers=ctx.no_headers,
            table_format=ctx.table_format,
            sort_by=ctx.sort_by,
        )
    )


@cli.command("update")
@click.argument("ref", required=True)
@click.option("--json", required=True, help="JSON payload or '-' for stdin.")
@pass_context
def update(ctx: Configuration, ref: str, json: str) -> None:
    """Update stored script configuration."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    result = api.update_collection_item_config(
        ctx,
        "script",
        collection.entity_slug(item["entity_id"]),
        _load_json(json),
    )
    ctx.echo(
        raw_format_output(
            ctx.output,
            result,
            ctx.yaml(),
            no_headers=ctx.no_headers,
            table_format=ctx.table_format,
            sort_by=ctx.sort_by,
        )
    )


@cli.command("run")
@click.argument("ref", required=True)
@click.option(
    "--arguments", help="Comma separated key/value pairs to use as arguments."
)
@pass_context
def run(ctx: Configuration, ref: str, arguments: str) -> None:
    """Run a script."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    data = to_attributes(arguments)
    data["entity_id"] = item["entity_id"]
    ctx.echo(format_output(ctx, api.call_service(ctx, "script", "turn_on", data)))


@cli.command("stop")
@click.argument("ref", required=True)
@pass_context
def stop(ctx: Configuration, ref: str) -> None:
    """Stop a running script."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    ctx.echo(
        format_output(
            ctx,
            api.call_service(
                ctx,
                "script",
                "turn_off",
                {"entity_id": item["entity_id"]},
            ),
        )
    )
