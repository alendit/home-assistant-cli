"""Helper plugin for Home Assistant CLI (hass-cli)."""

import logging
import sys
from typing import Any, Dict, List, Optional

import click

import homeassistant_cli.collection as collection
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, raw_format_output

_LOGGING = logging.getLogger(__name__)

HELPER_DOMAINS = (
    "counter",
    "input_boolean",
    "input_button",
    "input_datetime",
    "input_number",
    "input_select",
    "input_text",
    "timer",
)

COLS = [
    ("TYPE", "domain"),
    ("ENTITY", "entity_id"),
    ("NAME", "attributes.friendly_name"),
    ("STATE", "state"),
]


@click.group("helper")
@pass_context
def cli(ctx: Configuration) -> None:
    """Discover helper entities from Home Assistant."""
    ctx.auto_output("table")


def _helpers(
    ctx: Configuration, helper_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return helper entities from supported helper domains."""
    domains = [helper_type] if helper_type else list(HELPER_DOMAINS)
    result = []  # type: List[Dict[str, Any]]
    for domain in domains:
        for item in collection.get_domain_states(ctx, domain):
            result.append({**item, "domain": domain})
    return result


def _resolve(
    ctx: Configuration, ref: str, helper_type: Optional[str]
) -> Dict[str, Any]:
    """Resolve a helper ref."""
    try:
        item = collection.resolve_item(_helpers(ctx, helper_type), ref)
    except ValueError as ex:
        _LOGGING.error(str(ex))
        sys.exit(1)

    if not item:
        _LOGGING.error("Could not find helper with ref: %s", ref)
        sys.exit(1)

    return item


@cli.command("list")
@click.argument("helperfilter", default=".*", required=False)
@click.option("--type", "helper_type", type=click.Choice(HELPER_DOMAINS))
@pass_context
def list_cmd(ctx: Configuration, helperfilter: str, helper_type: Optional[str]) -> None:
    """List helpers."""
    ctx.auto_output("table")
    items = _helpers(ctx, helper_type)
    result = (
        items if helperfilter == ".*" else collection.filter_items(items, helperfilter)
    )
    ctx.echo(format_output(ctx, result, columns=ctx.columns if ctx.columns else COLS))


@cli.command("find")
@click.argument("pattern", required=True)
@click.option("--type", "helper_type", type=click.Choice(HELPER_DOMAINS))
@pass_context
def find_cmd(ctx: Configuration, pattern: str, helper_type: Optional[str]) -> None:
    """Find helpers by regex."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            collection.filter_items(_helpers(ctx, helper_type), pattern),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("show")
@click.argument("ref", required=True)
@click.option("--type", "helper_type", type=click.Choice(HELPER_DOMAINS))
@pass_context
def show(ctx: Configuration, ref: str, helper_type: Optional[str]) -> None:
    """Show the current helper entity state."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref, helper_type)
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
