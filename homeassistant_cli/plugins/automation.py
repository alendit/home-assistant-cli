"""Automation plugin for Home Assistant CLI (hass-cli)."""

import json as json_
import logging
import sys
from typing import Any, Dict, List, Optional, Sequence, cast

import click

import homeassistant_cli.collection as collection
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.exceptions import HomeAssistantCliError
from homeassistant_cli.helper import format_output, raw_format_output
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)

COLS = [
    ("ENTITY", "entity_id"),
    ("NAME", "attributes.friendly_name"),
    ("ID", "attributes.id"),
    ("STATE", "state"),
    ("LAST_TRIGGERED", "attributes.last_triggered"),
]


@click.group("automation")
@pass_context
def cli(ctx: Configuration) -> None:
    """Work with automations from Home Assistant."""
    ctx.auto_output("table")


def _automation_id(item: Dict[str, Any]) -> Sequence[Optional[str]]:
    """Return the automation config id for resolution."""
    return [item.get("attributes", {}).get("id")]


def _automations(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return automation states only."""
    return collection.get_domain_states(ctx, "automation")


def _resolve(ctx: Configuration, ref: str) -> Dict[str, Any]:
    """Resolve an automation ref."""
    if ref.startswith("automation."):
        try:
            item = api.get_state(ctx, ref)
        except HomeAssistantCliError:
            item = None
        if item and item.get("entity_id") == ref:
            return item

    try:
        item = collection.resolve_item(_automations(ctx), ref, [_automation_id])
    except ValueError as ex:
        _LOGGING.error(str(ex))
        sys.exit(1)

    if not item:
        _LOGGING.error("Could not find automation with ref: %s", ref)
        sys.exit(1)

    return item


def _load_json(source: str) -> Dict[str, Any]:
    """Load JSON from option value or stdin."""
    return cast(
        Dict[str, Any],
        json_.loads(source if source != "-" else click.get_text_stream("stdin").read()),
    )


def _automation_config_id_from_item(item: Dict[str, Any]) -> str:
    """Return the automation config id."""
    automation_id = item.get("attributes", {}).get("id")
    if not automation_id:
        _LOGGING.error(
            "Automation %s does not expose a config id", item.get("entity_id")
        )
        sys.exit(1)

    return cast(str, automation_id)


def _automation_config_id(ctx: Configuration, ref: str) -> str:
    """Return the automation config id."""
    if ref.startswith("automation."):
        return _automation_config_id_from_item(_resolve(ctx, ref))

    try:
        api.get_collection_item_config(ctx, "automation", ref)
    except HomeAssistantCliError:
        item = _resolve(ctx, ref)
        return _automation_config_id_from_item(item)

    return ref


def _automation_config_for_item(
    ctx: Configuration, item: Dict[str, Any]
) -> tuple[str, Dict[str, Any]]:
    """Return the automation config id and stored payload."""
    automation_id = _automation_config_id_from_item(item)
    return automation_id, api.get_collection_item_config(
        ctx, "automation", automation_id
    )


def _automation_config(ctx: Configuration, ref: str) -> tuple[str, Dict[str, Any]]:
    """Return the automation config id and stored payload."""
    if ref.startswith("automation."):
        return _automation_config_for_item(ctx, _resolve(ctx, ref))

    try:
        payload = api.get_collection_item_config(ctx, "automation", ref)
    except HomeAssistantCliError:
        return _automation_config_for_item(ctx, _resolve(ctx, ref))

    return ref, payload


def _call(ctx: Configuration, service: str, ref: str) -> None:
    """Call an automation service against a resolved ref."""
    entity_id = _resolve(ctx, ref)["entity_id"]
    result = api.call_service(ctx, "automation", service, {"entity_id": entity_id})
    ctx.echo(format_output(ctx, result))


@cli.command("list")
@click.argument("automationfilter", default=".*", required=False)
@pass_context
def list_cmd(ctx: Configuration, automationfilter: str) -> None:
    """List automations."""
    ctx.auto_output("table")
    items = _automations(ctx)
    result = (
        items
        if automationfilter == ".*"
        else collection.filter_items(items, automationfilter)
    )
    ctx.echo(format_output(ctx, result, columns=ctx.columns if ctx.columns else COLS))


@cli.command("find")
@click.argument("pattern", required=True)
@pass_context
def find_cmd(ctx: Configuration, pattern: str) -> None:
    """Find automations by regex."""
    ctx.auto_output("table")
    ctx.echo(
        format_output(
            ctx,
            collection.filter_items(_automations(ctx), pattern),
            columns=ctx.columns if ctx.columns else COLS,
        )
    )


@cli.command("show")
@click.argument("ref", required=True)
@pass_context
def show(ctx: Configuration, ref: str) -> None:
    """Show runtime state plus stored automation configuration."""
    ctx.auto_output("data")
    item = _resolve(ctx, ref)
    _, payload = _automation_config_for_item(ctx, item)
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


@cli.command("export")
@click.argument("ref", required=True)
@pass_context
def export(ctx: Configuration, ref: str) -> None:
    """Export the update-safe stored automation configuration."""
    ctx.auto_output("data")
    _, payload = _automation_config(ctx, ref)
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
@click.option(
    "--json",
    required=True,
    help="Full JSON payload matching `automation export`, or '-' for stdin.",
)
@pass_context
def update(ctx: Configuration, ref: str, json: str) -> None:
    """Update stored automation configuration."""
    ctx.auto_output("data")
    automation_id = _automation_config_id(ctx, ref)
    result = api.update_collection_item_config(
        ctx, "automation", automation_id, _load_json(json)
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


@cli.command("patch")
@click.argument("ref", required=True)
@click.option(
    "--json",
    required=True,
    help="Inline JSON merge patch to apply on top of `automation export` output.",
)
@pass_context
def patch(ctx: Configuration, ref: str, json: str) -> None:
    """Patch stored automation configuration with an inline JSON merge patch."""
    ctx.auto_output("data")
    automation_id, payload = _automation_config(ctx, ref)
    result = api.update_collection_item_config(
        ctx,
        "automation",
        automation_id,
        collection.merge_patch(payload, _load_json(json)),
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


@cli.command("trigger")
@click.argument("ref", required=True)
@pass_context
def trigger(ctx: Configuration, ref: str) -> None:
    """Trigger an automation."""
    ctx.auto_output("data")
    _call(ctx, "trigger", ref)


@cli.command("enable")
@click.argument("ref", required=True)
@pass_context
def enable(ctx: Configuration, ref: str) -> None:
    """Enable an automation."""
    ctx.auto_output("data")
    _call(ctx, "turn_on", ref)


@cli.command("disable")
@click.argument("ref", required=True)
@pass_context
def disable(ctx: Configuration, ref: str) -> None:
    """Disable an automation."""
    ctx.auto_output("data")
    _call(ctx, "turn_off", ref)
