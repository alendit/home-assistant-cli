"""Energy dashboard commands for Home Assistant CLI (hass-cli)."""

import logging
import sys
from typing import Any, Dict, Optional

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, load_json_input, raw_format_output
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)

DEVICE_COLS = [
    ("NAME", "name"),
    ("CONSUMPTION", "stat_consumption"),
    ("RATE", "stat_rate"),
]
GRID_COLS = [
    ("FROM", "stat_energy_from"),
    ("TO", "stat_energy_to"),
    ("COST", "stat_cost"),
    ("PRICE", "entity_energy_price"),
]


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


def _prefs(ctx: Configuration) -> Dict[str, Any]:
    """Return current Energy preferences."""
    return api.energy_get_prefs(ctx)


def _save(ctx: Configuration, prefs: Dict[str, Any]) -> None:
    """Persist Energy preferences and print the saved payload."""
    _show_data(ctx, api.energy_save_prefs(ctx, prefs))


@click.group("energy")
@pass_context
def cli(ctx: Configuration) -> None:
    """Inspect and manage Energy dashboard preferences."""
    ctx.auto_output("data")


@cli.command("show")
@pass_context
def show(ctx: Configuration) -> None:
    """Show the current Energy dashboard preferences."""
    _show_data(ctx, _prefs(ctx))


@cli.command("validate")
@pass_context
def validate(ctx: Configuration) -> None:
    """Validate the current Energy dashboard preferences."""
    _show_data(ctx, api.energy_validate(ctx))


@cli.command("save")
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def save(ctx: Configuration, json: Optional[str], json_file: Optional[str]) -> None:
    """Replace the current Energy dashboard preferences."""
    payload = load_json_input(json, json_file)
    if not isinstance(payload, dict):
        raise click.UsageError("Energy preferences must be a JSON object")

    _save(ctx, payload)


@cli.group("device")
@pass_context
def device(ctx: Configuration) -> None:
    """Manage Energy dashboard individual devices."""
    ctx.auto_output("data")


@device.command("list")
@pass_context
def device_list(ctx: Configuration) -> None:
    """List configured Energy dashboard individual devices."""
    ctx.auto_output("table")
    items = _prefs(ctx).get("device_consumption", [])
    ctx.echo(
        format_output(ctx, items, columns=ctx.columns if ctx.columns else DEVICE_COLS)
    )


@device.command("add")
@click.argument("stat_consumption", required=True)
@click.option("--rate", "stat_rate")
@click.option("--name")
@pass_context
def device_add(
    ctx: Configuration,
    stat_consumption: str,
    stat_rate: Optional[str],
    name: Optional[str],
) -> None:
    """Add or update an Energy dashboard individual device."""
    prefs = _prefs(ctx)
    devices = list(prefs.get("device_consumption", []))
    new_item: Dict[str, Any] = {"stat_consumption": stat_consumption}
    if stat_rate:
        new_item["stat_rate"] = stat_rate
    if name:
        new_item["name"] = name

    for index, item in enumerate(devices):
        if item.get("stat_consumption") == stat_consumption:
            devices[index] = {**item, **new_item}
            break
    else:
        devices.append(new_item)

    prefs["device_consumption"] = devices
    _save(ctx, prefs)


@device.command("remove")
@click.argument("ref", required=True)
@pass_context
def device_remove(ctx: Configuration, ref: str) -> None:
    """Remove an Energy dashboard individual device by name or sensor."""
    prefs = _prefs(ctx)
    devices = list(prefs.get("device_consumption", []))
    filtered = [
        item
        for item in devices
        if item.get("stat_consumption") != ref and item.get("name") != ref
    ]
    if len(filtered) == len(devices):
        _LOGGING.error("Could not find energy device with ref: %s", ref)
        sys.exit(1)

    prefs["device_consumption"] = filtered
    _save(ctx, prefs)


@cli.group("grid")
@pass_context
def grid(ctx: Configuration) -> None:
    """Manage Energy dashboard grid sources."""
    ctx.auto_output("data")


@grid.command("list")
@pass_context
def grid_list(ctx: Configuration) -> None:
    """List configured grid sources."""
    ctx.auto_output("table")
    items = [
        item
        for item in _prefs(ctx).get("energy_sources", [])
        if item.get("type") == "grid"
    ]
    ctx.echo(
        format_output(ctx, items, columns=ctx.columns if ctx.columns else GRID_COLS)
    )


@grid.command("clear")
@pass_context
def grid_clear(ctx: Configuration) -> None:
    """Remove all configured grid sources."""
    prefs = _prefs(ctx)
    prefs["energy_sources"] = [
        item for item in prefs.get("energy_sources", []) if item.get("type") != "grid"
    ]
    _save(ctx, prefs)


@grid.command("set")
@click.option("--energy-from", "stat_energy_from", required=True)
@click.option("--energy-to", "stat_energy_to")
@click.option("--cost", "stat_cost")
@click.option("--price-entity", "entity_energy_price")
@click.option("--price-number", "number_energy_price")
@click.option("--compensation", "stat_compensation")
@click.option("--price-export-entity", "entity_energy_price_export")
@click.option("--price-export-number", "number_energy_price_export")
@click.option("--cost-adjustment-day", default=0.0, type=float, show_default=True)
@pass_context
def grid_set(
    ctx: Configuration,
    stat_energy_from: str,
    stat_energy_to: Optional[str],
    stat_cost: Optional[str],
    entity_energy_price: Optional[str],
    number_energy_price: Optional[str],
    stat_compensation: Optional[str],
    entity_energy_price_export: Optional[str],
    number_energy_price_export: Optional[str],
    cost_adjustment_day: float,
) -> None:
    """Set the configured grid source."""
    prefs = _prefs(ctx)
    others = [
        item for item in prefs.get("energy_sources", []) if item.get("type") != "grid"
    ]
    grid_source: Dict[str, Any] = {
        "type": "grid",
        "cost_adjustment_day": cost_adjustment_day,
        "stat_energy_from": stat_energy_from,
        "stat_cost": stat_cost,
        "entity_energy_price": entity_energy_price,
        "number_energy_price": number_energy_price,
        "stat_energy_to": stat_energy_to,
        "stat_compensation": stat_compensation,
        "entity_energy_price_export": entity_energy_price_export,
        "number_energy_price_export": number_energy_price_export,
    }

    prefs["energy_sources"] = [*others, grid_source]
    _save(ctx, prefs)
