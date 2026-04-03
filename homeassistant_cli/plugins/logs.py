"""Logs plugin for Home Assistant CLI (hass-cli)."""

import re
from typing import List

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
import homeassistant_cli.remote as api

_RECORD_START = re.compile(r"^\d{4}-\d{2}-\d{2} ")


def _split_records(log_text: str) -> List[str]:
    """Split Home Assistant log text into timestamp-prefixed records."""
    records: List[str] = []
    current: List[str] = []

    for line in log_text.splitlines():
        if _RECORD_START.match(line):
            if current:
                records.append("\n".join(current))
            current = [line]
            continue

        if current:
            current.append(line)
        else:
            current = [line]

    if current:
        records.append("\n".join(current))

    return records


def _match_tokens(target: str) -> List[str]:
    """Generate likely logger tokens for an integration name."""
    raw = str(target or "").strip()
    if not raw:
        return []

    normalized = raw.replace("-", "_")
    tokens = [
        raw,
        normalized,
        normalized.replace("_", "-"),
        f"[custom_components.{normalized}]",
        f"[homeassistant.components.{normalized}]",
        f"[homeassistant.helpers.{normalized}]",
        f"[{normalized}]",
    ]

    results: List[str] = []
    for token in tokens:
        if token and token not in results:
            results.append(token)
    return results


def _filter_records(log_text: str, target: str, ignore_case: bool = True) -> str:
    """Filter log records by an integration/logger token."""
    if not target:
        return log_text

    needles = _match_tokens(target)
    if ignore_case:
        needles = [needle.lower() for needle in needles]

    matched: List[str] = []
    for record in _split_records(log_text):
        haystack = record.lower() if ignore_case else record
        if any(needle in haystack for needle in needles):
            matched.append(record)

    return "\n".join(matched)


@click.command("logs")
@click.argument("target", required=False)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Match the provided token with case sensitivity.",
)
@pass_context
def cli(ctx: Configuration, target: str | None, case_sensitive: bool) -> None:
    """Read Home Assistant error logs, optionally filtered by integration."""
    log_text = api.get_raw_error_log(ctx)
    click.echo(_filter_records(log_text, target or "", ignore_case=not case_sensitive))
