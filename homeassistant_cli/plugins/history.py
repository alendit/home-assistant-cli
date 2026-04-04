"""History plugin for Home Assistant CLI (hass-cli)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

import click
import dateparser

import homeassistant_cli.autocompletion as autocompletion
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
import homeassistant_cli.const as const
import homeassistant_cli.helper as helper
import homeassistant_cli.remote as api

_DATEPARSER_SETTINGS = {
    "DATE_ORDER": "DMY",
    "TIMEZONE": "UTC",
    "RETURN_AS_TIMEZONE_AWARE": True,
}

_SUMMARY_COLUMNS = [
    ("entity_id", "entity_id"),
    ("average", "average"),
    ("minimum", "minimum"),
    ("maximum", "maximum"),
    ("coverage_pct", "coverage_pct"),
    ("valid_points", "valid_points"),
    ("invalid_points", "invalid_points"),
]

_AVERAGE_COLUMNS = [
    ("entity_id", "entity_id"),
    ("average", "average"),
    ("coverage_pct", "coverage_pct"),
    ("coverage_hours", "coverage_hours"),
]


@click.group("history")
@pass_context
def cli(ctx: Configuration) -> None:
    """Inspect Home Assistant recorder history."""
    ctx.auto_output("table")


@cli.command("get")
@click.argument(
    "entities",
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,
)
@click.option(
    "--since",
    required=False,
    default="1d",
    help="Start of the period to get history from.",
)
@click.option(
    "--end",
    required=False,
    default="now",
    help="End of the period to query history from.",
)
@pass_context
def get(ctx: Configuration, entities: Tuple[str, ...], since: str, end: str) -> None:
    """Get raw recorder history for one or more entities."""
    start_time, end_time = _parse_range(since, end)
    data = api.get_history(ctx, list(entities), start_time, end_time)
    flattened: List[Dict[str, Any]] = []
    for item in data:
        flattened.extend(item)

    ctx.echo(
        helper.format_output(
            ctx,
            flattened,
            columns=ctx.columns if ctx.columns else const.COLUMNS_ENTITIES,
        )
    )


@cli.command("summary")
@click.argument(
    "entities",
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,
)
@click.option(
    "--since",
    required=False,
    default="1d",
    help="Start of the period to summarize.",
)
@click.option(
    "--end",
    required=False,
    default="now",
    help="End of the period to summarize.",
)
@pass_context
def summary(
    ctx: Configuration, entities: Tuple[str, ...], since: str, end: str
) -> None:
    """Summarize recorder history with a time-weighted average."""
    start_time, end_time = _parse_range(since, end)
    histories = api.get_history(ctx, list(entities), start_time, end_time)
    result = _summaries_for_entities(entities, histories, start_time, end_time)
    ctx.echo(helper.format_output(ctx, result, columns=_SUMMARY_COLUMNS))


@cli.command("average")
@click.argument(
    "entities",
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,
)
@click.option(
    "--since",
    required=False,
    default="1d",
    help="Start of the period to average.",
)
@click.option(
    "--end",
    required=False,
    default="now",
    help="End of the period to average.",
)
@pass_context
def average(
    ctx: Configuration, entities: Tuple[str, ...], since: str, end: str
) -> None:
    """Return a time-weighted average for one or more entities."""
    start_time, end_time = _parse_range(since, end)
    histories = api.get_history(ctx, list(entities), start_time, end_time)
    result = _summaries_for_entities(entities, histories, start_time, end_time)
    averages = [
        {
            "entity_id": row["entity_id"],
            "average": row["average"],
            "coverage_pct": row["coverage_pct"],
            "coverage_hours": row["coverage_hours"],
        }
        for row in result
    ]
    ctx.echo(helper.format_output(ctx, averages, columns=_AVERAGE_COLUMNS))


def _parse_range(since: str, end: str) -> tuple[datetime, datetime]:
    """Parse one CLI history range."""
    start_time = _parse_datetime(since)
    end_time = _parse_datetime(end)
    if start_time is None or end_time is None:
        raise click.UsageError("Could not parse the provided history date range.")
    if start_time >= end_time:
        raise click.UsageError("--since must be earlier than --end.")
    return start_time, end_time


def _summaries_for_entities(
    requested_entities: Sequence[str],
    histories: Sequence[Sequence[Dict[str, Any]]],
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """Build one summary row per requested entity."""
    result: List[Dict[str, Any]] = []
    for idx, requested in enumerate(requested_entities):
        items = list(histories[idx]) if idx < len(histories) else []
        entity_id = _entity_id_from_history(items) or requested
        result.append(_summarize_history(entity_id, items, start_time, end_time))
    return result


def _entity_id_from_history(items: Sequence[Dict[str, Any]]) -> str | None:
    """Extract the entity id from a history payload when available."""
    for item in items:
        entity_id = item.get("entity_id")
        if isinstance(entity_id, str) and entity_id:
            return entity_id
    return None


def _summarize_history(
    entity_id: str,
    items: Sequence[Dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    """Summarize one entity history payload."""
    ordered = sorted(
        [item for item in items if isinstance(item, dict)],
        key=lambda item: _parse_item_time(item),
    )
    total_seconds = max((end_time - start_time).total_seconds(), 0.0)
    coverage_seconds = 0.0
    weighted_sum = 0.0
    minimum: float | None = None
    maximum: float | None = None
    valid_points = 0
    invalid_points = 0

    for idx, item in enumerate(ordered):
        current_time = _parse_item_time(item)
        next_time = (
            _parse_item_time(ordered[idx + 1]) if idx + 1 < len(ordered) else end_time
        )
        segment_start = max(current_time, start_time)
        segment_end = min(next_time, end_time)
        if segment_end <= segment_start:
            continue

        value = _coerce_numeric_state(item.get("state"))
        if value is None:
            invalid_points += 1
            continue

        valid_points += 1
        duration = (segment_end - segment_start).total_seconds()
        coverage_seconds += duration
        weighted_sum += value * duration
        minimum = value if minimum is None else min(minimum, value)
        maximum = value if maximum is None else max(maximum, value)

    average = weighted_sum / coverage_seconds if coverage_seconds else None
    coverage_pct = (coverage_seconds / total_seconds * 100.0) if total_seconds else 0.0

    return {
        "entity_id": entity_id,
        "average": _round_float(average),
        "minimum": _round_float(minimum),
        "maximum": _round_float(maximum),
        "coverage_pct": _round_float(coverage_pct),
        "coverage_hours": _round_float(coverage_seconds / 3600.0),
        "window_hours": _round_float(total_seconds / 3600.0),
        "valid_points": valid_points,
        "invalid_points": invalid_points,
    }


def _parse_item_time(item: Dict[str, Any]) -> datetime:
    """Parse one history item timestamp."""
    raw = item.get("last_changed") or item.get("last_updated")
    if not isinstance(raw, str):
        raise click.ClickException("History item is missing a timestamp.")
    parsed = _parse_datetime(raw)
    if parsed is None:
        raise click.ClickException(f"Could not parse history timestamp: {raw}")
    return parsed


def _parse_datetime(value: str) -> datetime | None:
    """Parse either an ISO timestamp or a relative date expression."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return datetime.fromisoformat(stripped)
    except ValueError:
        return dateparser.parse(stripped, settings=_DATEPARSER_SETTINGS)


def _coerce_numeric_state(value: Any) -> float | None:
    """Convert one state string to a float when possible."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.lower() in {"unknown", "unavailable", "none", "null"}:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def _round_float(value: float | None) -> float | None:
    """Round floats for stable CLI output."""
    if value is None:
        return None
    return round(value, 3)
