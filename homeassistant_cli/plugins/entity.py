"""Entity plugin for Home Assistant CLI (hass-cli)."""

import logging
import re
import sys
from typing import Any, Dict, List, Optional

import click

import homeassistant_cli.autocompletion as autocompletion
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
import homeassistant_cli.const as const
import homeassistant_cli.helper as helper
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)


@click.group("entity")
@pass_context
def cli(ctx: Configuration) -> None:
    """Get info on entities from Home Assistant."""


@cli.command("list")
@click.argument("entityfilter", default=".*", required=False)
@pass_context
def listcmd(ctx: Configuration, entityfilter: str) -> None:
    """List all entities from Home Assistant."""
    ctx.auto_output("table")

    areas = api.get_areas(ctx)

    entities = api.get_entities(ctx)

    result: List[Dict[str, Any]] = []
    if entityfilter == ".*":
        result = entities
    else:
        entityfilterre = re.compile(entityfilter)

        for entity in entities:
            if entityfilterre.search(entity["entity_id"]):
                result.append(entity)

    for entity in entities:
        area = next((a for a in areas if a["area_id"] == entity["area_id"]), None)
        if area:
            entity["area_name"] = area["name"]

    cols = [
        ("ENTITY_ID", "entity_id"),
        ("NAME", "name"),
        ("DEVICE_ID", "device_id"),
        ("PLATFORM", "platform"),
        ("AREA", "area_name"),
        ("CONFIG_ENTRY_ID", "config_entry_id"),
        ("DISABLED_BY", "disabled_by"),
    ]

    ctx.echo(
        helper.format_output(ctx, result, columns=ctx.columns if ctx.columns else cols)
    )


@cli.command("assign")
@click.argument(
    "area_id_or_name",
    required=True,
    shell_complete=autocompletion.areas,
)
@click.argument("names", nargs=-1, required=False)
@click.option("--match", help="Expression used to find entities matching that name")
@pass_context
def assign(
    ctx: Configuration,
    area_id_or_name: str,
    names: tuple[str, ...],
    match: Optional[str] = None,
) -> None:
    """Update area on one or more entities.

    NAMES - one or more name or id (Optional)
    """
    ctx.auto_output("data")

    entities = api.get_entities(ctx)

    result: List[Dict[str, Any]] = []

    area = api.find_area(ctx, area_id_or_name)
    if not area:
        _LOGGING.error("Could not find area with id or name: %s", area_id_or_name)
        sys.exit(1)

    if match:
        if match == ".*":
            result = entities
        else:
            entityfilterre = re.compile(match)

            for entity in entities:
                if entityfilterre.search(entity["name"]):
                    result.append(entity)

    for id_or_name in names:
        found_entity: Optional[Dict[str, Any]] = next(
            (x for x in entities if x["entity_id"] == id_or_name), None
        )
        if not found_entity:
            found_entity = next((x for x in entities if x["name"] == id_or_name), None)
        if not found_entity:
            _LOGGING.error("Could not find entity with id or name: %s", id_or_name)
            sys.exit(1)
        result.append(found_entity)

    for entity in result:
        output = api.assign_entity_area(ctx, entity["entity_id"], area["area_id"])
        if output["success"]:
            ctx.echo(
                "Successfully assigned '{}' to '{}'".format(
                    area["name"], entity["entity_id"]
                )
            )
        else:
            _LOGGING.error(
                "Failed to assign '%s' to '%s'",
                area["name"],
                entity["entity_id"],
            )

            ctx.echo(str(output))


@cli.command("rename")
@click.argument(
    "oldid",
    required=True,
    shell_complete=autocompletion.entities,
)
@click.option("--name", required=False)
@click.argument(
    "newid",
    required=False,
    shell_complete=autocompletion.entities,
)
@pass_context
def rename(
    ctx: Configuration,
    oldid: str,
    newid: Optional[str],
    name: Optional[str],
) -> None:
    """Rename a entity."""
    ctx.auto_output("data")

    if not newid and not name:
        _LOGGING.error("Need to at least specify either a new id or new name")
        sys.exit(1)

    entity = api.get_entity(ctx, oldid)
    if not entity:
        _LOGGING.error("Could not find entity with ID: %s", oldid)
        sys.exit(1)

    result = api.rename_entity(ctx, oldid, newid, name)

    ctx.echo(
        helper.format_output(
            ctx,
            [result],
            columns=ctx.columns if ctx.columns else const.COLUMNS_DEFAULT,
        )
    )
