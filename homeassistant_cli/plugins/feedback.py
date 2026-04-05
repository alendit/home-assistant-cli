"""Feedback plugin for Home Assistant CLI (hass-cli)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, raw_format_output
import homeassistant_cli.remote as api

DEFAULT_FEEDBACK_LIST = "Codex Feedback"
LOCAL_TODO_DOMAIN = "local_todo"
TODO_DOMAIN = "todo"
TODO_STATUS_COMPLETED = "completed"
TODO_STATUS_NEEDS_ACTION = "needs_action"

COLS = [
    ("ID", "feedback_id"),
    ("STATUS", "status"),
    ("CREATED", "created_at"),
    ("ISSUE", "issue"),
    ("SOURCE", "source"),
]


def _render_data(ctx: Configuration, data: Any) -> None:
    """Render a single payload using the active output mode."""
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


def _slugify(value: str) -> str:
    """Return a stable entity-style slug for one title."""
    slug = ""
    last_was_sep = False
    for char in str(value or "").strip().lower():
        if char.isalnum():
            slug += char
            last_was_sep = False
            continue
        if not last_was_sep:
            slug += "_"
            last_was_sep = True
    return slug.strip("_")


def _feedback_entry(ctx: Configuration, list_name: str) -> Optional[Dict[str, Any]]:
    """Return the Local To-do entry backing one feedback list, if it exists."""
    for entry in api.get_config_entries(ctx):
        if entry.get("domain") != LOCAL_TODO_DOMAIN:
            continue
        if entry.get("title") == list_name:
            return entry
    return None


def _feedback_entity(
    ctx: Configuration, entry_id: str, list_name: str
) -> Optional[str]:
    """Resolve the todo entity backing one feedback list."""
    entities = api.get_entities(ctx)
    for entity in entities:
        if entity.get("config_entry_id") != entry_id:
            continue
        entity_id = entity.get("entity_id")
        if isinstance(entity_id, str) and entity_id.startswith("todo."):
            return entity_id
    fallback = _slugify(list_name)
    return f"todo.{fallback}" if fallback else None


def _ensure_feedback_entity(ctx: Configuration, list_name: str) -> str:
    """Return the feedback entity id, creating the Local To-do list if needed."""
    entry = _feedback_entry(ctx, list_name)
    if entry is None:
        handlers = api.get_config_entry_flow_handlers(ctx)
        if LOCAL_TODO_DOMAIN not in handlers:
            raise click.ClickException(
                "Home Assistant does not expose the local_todo config-entry flow."
            )
        result = api.init_config_entry_flow(ctx, LOCAL_TODO_DOMAIN)
        flow_id = result.get("flow_id")
        if result.get("type") != "form" or not isinstance(flow_id, str):
            raise click.ClickException(
                f"Unexpected local_todo flow response: {json.dumps(result)}"
            )
        result = api.continue_config_entry_flow(
            ctx,
            flow_id,
            {"todo_list_name": list_name},
        )
        if result.get("type") not in {"create_entry", "abort"}:
            raise click.ClickException(
                f"Unexpected local_todo create response: {json.dumps(result)}"
            )
        entry = _feedback_entry(ctx, list_name)
        if entry is None:
            raise click.ClickException(
                "Created the Local To-do feedback list but could not find the config entry."
            )

    entry_id = entry.get("entry_id")
    if not isinstance(entry_id, str) or not entry_id:
        raise click.ClickException("Feedback config entry is missing an entry_id.")
    entity_id = _feedback_entity(ctx, entry_id, list_name)
    if entity_id is None:
        raise click.ClickException("Could not resolve the feedback todo entity.")
    return entity_id


def _resolve_feedback_entity(
    ctx: Configuration,
    entity_id: Optional[str],
    list_name: str,
    *,
    create_if_missing: bool,
) -> Optional[str]:
    """Resolve an explicit or implicit feedback entity id."""
    if entity_id:
        return entity_id
    if create_if_missing:
        return _ensure_feedback_entity(ctx, list_name)
    entry = _feedback_entry(ctx, list_name)
    if entry is None:
        return None
    entry_id = entry.get("entry_id")
    if not isinstance(entry_id, str) or not entry_id:
        return None
    return _feedback_entity(ctx, entry_id, list_name)


def _parse_feedback_item(entity_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one todo item into one CLI feedback record."""
    metadata: Dict[str, Any] = {}
    description = item.get("description")
    if isinstance(description, str) and description.strip():
        try:
            parsed = json.loads(description)
        except ValueError:
            parsed = {"details": description}
        if isinstance(parsed, dict):
            metadata = parsed

    suggestions = metadata.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    return {
        "feedback_id": item.get("uid"),
        "issue": item.get("summary"),
        "status": item.get("status") or TODO_STATUS_NEEDS_ACTION,
        "created_at": metadata.get("created_at"),
        "completed_at": item.get("completed"),
        "source": metadata.get("source"),
        "session_key": metadata.get("session_key"),
        "turn_id": metadata.get("turn_id"),
        "profile": metadata.get("profile"),
        "details": metadata.get("details"),
        "suggestions": suggestions,
        "suggestions_text": "; ".join(str(value) for value in suggestions),
        "entity_id": entity_id,
    }


def _load_feedback_items(ctx: Configuration, entity_id: str) -> List[Dict[str, Any]]:
    """Return parsed feedback items for one entity, newest first."""
    items = [
        _parse_feedback_item(entity_id, item)
        for item in api.get_todo_items(ctx, entity_id)
        if isinstance(item, dict)
    ]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return items


@click.group("feedback")
@pass_context
def cli(ctx: Configuration) -> None:
    """Store and review Codex operator feedback in Home Assistant."""


@cli.command("submit")
@click.argument("issue", required=True)
@click.option(
    "--suggestion",
    "suggestions",
    multiple=True,
    help="Suggested improvement to store alongside the issue. Repeat as needed.",
)
@click.option("--details", help="Additional context for the feedback entry.")
@click.option("--session-key", help="Optional Home Assistant or Codex session key.")
@click.option("--turn-id", help="Optional Codex turn id.")
@click.option("--profile", help="Optional Codex profile name.")
@click.option("--source", default="agent", show_default=True)
@click.option("--entity-id", help="Explicit todo entity id to use as the backing list.")
@click.option(
    "--list-name",
    default=DEFAULT_FEEDBACK_LIST,
    show_default=True,
    help="Local To-do list title used when no explicit entity_id is provided.",
)
@pass_context
def submit(
    ctx: Configuration,
    issue: str,
    suggestions: tuple[str, ...],
    details: Optional[str],
    session_key: Optional[str],
    turn_id: Optional[str],
    profile: Optional[str],
    source: str,
    entity_id: Optional[str],
    list_name: str,
) -> None:
    """Store one new feedback item."""
    ctx.auto_output("data")
    target_entity_id = _resolve_feedback_entity(
        ctx,
        entity_id,
        list_name,
        create_if_missing=True,
    )
    assert target_entity_id is not None

    created_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "created_at": created_at,
        "source": source,
        "session_key": session_key,
        "turn_id": turn_id,
        "profile": profile,
        "suggestions": [item for item in suggestions if item.strip()],
        "details": details,
    }
    api.call_service(
        ctx,
        TODO_DOMAIN,
        "add_item",
        {
            "entity_id": target_entity_id,
            "item": issue,
            "description": json.dumps(payload, sort_keys=True),
        },
    )

    stored = next(
        (
            item
            for item in _load_feedback_items(ctx, target_entity_id)
            if item.get("issue") == issue and item.get("created_at") == created_at
        ),
        None,
    )
    if stored is None:
        stored = {
            "feedback_id": None,
            "issue": issue,
            "status": TODO_STATUS_NEEDS_ACTION,
            "created_at": created_at,
            "completed_at": None,
            "source": source,
            "session_key": session_key,
            "turn_id": turn_id,
            "profile": profile,
            "details": details,
            "suggestions": list(suggestions),
            "suggestions_text": "; ".join(suggestions),
            "entity_id": target_entity_id,
        }
    _render_data(ctx, stored)


@cli.command("retrieve")
@click.option(
    "--all",
    "include_all",
    is_flag=True,
    default=False,
    help="Include addressed feedback entries.",
)
@click.option("--entity-id", help="Explicit todo entity id to use as the backing list.")
@click.option(
    "--list-name",
    default=DEFAULT_FEEDBACK_LIST,
    show_default=True,
    help="Local To-do list title used when no explicit entity_id is provided.",
)
@pass_context
def retrieve(
    ctx: Configuration,
    include_all: bool,
    entity_id: Optional[str],
    list_name: str,
) -> None:
    """Retrieve stored feedback entries."""
    ctx.auto_output("table")
    target_entity_id = _resolve_feedback_entity(
        ctx,
        entity_id,
        list_name,
        create_if_missing=False,
    )
    if target_entity_id is None:
        ctx.echo(format_output(ctx, [], columns=ctx.columns if ctx.columns else COLS))
        return

    items = _load_feedback_items(ctx, target_entity_id)
    if not include_all:
        items = [
            item for item in items if item.get("status") != TODO_STATUS_COMPLETED
        ]
    ctx.echo(format_output(ctx, items, columns=ctx.columns if ctx.columns else COLS))


@cli.command("mark-done")
@click.argument("feedback_ids", nargs=-1, required=True)
@click.option("--entity-id", help="Explicit todo entity id to use as the backing list.")
@click.option(
    "--list-name",
    default=DEFAULT_FEEDBACK_LIST,
    show_default=True,
    help="Local To-do list title used when no explicit entity_id is provided.",
)
@pass_context
def mark_done(
    ctx: Configuration,
    feedback_ids: tuple[str, ...],
    entity_id: Optional[str],
    list_name: str,
) -> None:
    """Mark one or more feedback entries as addressed."""
    ctx.auto_output("data")
    target_entity_id = _resolve_feedback_entity(
        ctx,
        entity_id,
        list_name,
        create_if_missing=False,
    )
    if target_entity_id is None:
        raise click.ClickException("No feedback list has been created yet.")

    items = _load_feedback_items(ctx, target_entity_id)
    items_by_id = {
        str(item["feedback_id"]): item
        for item in items
        if isinstance(item.get("feedback_id"), str) and item["feedback_id"]
    }

    updated_ids: List[str] = []
    for feedback_id in feedback_ids:
        if feedback_id not in items_by_id:
            raise click.ClickException(f"Unknown feedback id: {feedback_id}")
        api.call_service(
            ctx,
            TODO_DOMAIN,
            "update_item",
            {
                "entity_id": target_entity_id,
                "item": feedback_id,
                "status": TODO_STATUS_COMPLETED,
            },
        )
        updated_ids.append(feedback_id)

    _render_data(
        ctx,
        {
            "updated_ids": updated_ids,
            "count": len(updated_ids),
            "entity_id": target_entity_id,
        },
    )
