"""Raw plugin for Home Assistant CLI (hass-cli)."""

import json as json_
import logging
from typing import Optional
from urllib.parse import urlsplit, urlunsplit
import re

import click
import requests

import homeassistant_cli.autocompletion as autocompletion
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import format_output, load_json_input
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)
_TIMESTAMP_OFFSET_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+\d{2}:\d{2}$"
)


@click.group("raw")
@pass_context
def cli(ctx: Configuration) -> None:
    """Call the raw API (advanced)."""
    ctx.auto_output("data")


def _report(
    ctx: Configuration, cmd: str, method: str, response: requests.Response
) -> None:
    """Create a report."""
    response.raise_for_status()

    if response.ok:
        try:
            ctx.echo(format_output(ctx, response.json()))
        except json_.decoder.JSONDecodeError:
            _LOGGING.debug("Response could not be parsed as JSON")
            ctx.echo(response.text)
    else:
        _LOGGING.warning(
            "%s: <No output returned from %s %s>",
            response.status_code,
            cmd,
            method,
        )


def _normalize_api_method(method: str) -> str:
    """Normalize raw REST methods to the Home Assistant API namespace.

    Accept bare method names such as ``config`` and normalize them to
    ``/api/config``. Absolute paths are preserved to keep the raw command
    usable for advanced cases outside the default API namespace.
    """
    if method.startswith("/api/"):
        return _normalize_query_timestamps(method)

    if method.startswith("api/"):
        return _normalize_query_timestamps(f"/{method}")

    if method.startswith("/"):
        return _normalize_query_timestamps(method)

    return _normalize_query_timestamps(f"/api/{method}")


def _normalize_query_timestamps(method: str) -> str:
    """Percent-encode literal timezone offsets inside query values.

    Requests leaves raw ``+`` characters in query strings untouched, but Home
    Assistant history endpoints expect timezone offsets such as ``+00:00`` to be
    percent-encoded when passed as query values.
    """
    parts = urlsplit(method)
    if not parts.query:
        return method

    normalized_parts = []
    for segment in parts.query.split("&"):
        if "=" not in segment:
            normalized_parts.append(segment)
            continue

        key, value = segment.split("=", 1)
        if "%" not in value and _TIMESTAMP_OFFSET_RE.match(value):
            value = value.replace("+", "%2B")
        normalized_parts.append(f"{key}={value}")

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            "&".join(normalized_parts),
            parts.fragment,
        )
    )


@cli.command()
@click.argument("method", shell_complete=autocompletion.api_methods)
@pass_context
def get(ctx: Configuration, method: str) -> None:
    """Do a GET request against /api/<method>.

    METHOD accepts `config`, `api/config`, or `/api/config`.
    """
    response = api.restapi(ctx, "get", _normalize_api_method(method))

    _report(ctx, "GET", method, response)


@cli.command()
@click.argument("method", shell_complete=autocompletion.api_methods)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def post(
    ctx: Configuration,
    method: str,
    json: Optional[str],
    json_file: Optional[str],
) -> None:
    """Do a POST request against /api/<method>.

    METHOD accepts `config`, `api/config`, or `/api/config`.
    """
    data = load_json_input(json, json_file)

    response = api.restapi(ctx, "post", _normalize_api_method(method), data)

    _report(ctx, "GET", method, response)


@cli.command("ws")
@click.argument("wstype", shell_complete=autocompletion.wsapi_methods)
@click.option("--json")
@click.option("--json-file", type=click.Path(exists=True, dir_okay=False))
@pass_context
def websocket(
    ctx: Configuration,
    wstype: str,
    json: Optional[str],
    json_file: Optional[str],
) -> None:
    r"""Send a websocket request against /api/websocket.

    WSTYPE is name of websocket methods.

    \b
    --json is dictionary to pass in addition to the type.
           Example: --json='{ "area_id":"2c8bf93c8082492f99c989896962f207" }'
    """
    data = load_json_input(json, json_file)
    if not isinstance(data, dict):
        raise click.UsageError("Websocket payload must be a JSON object")

    frame = {"type": wstype}
    frame = {**frame, **data}  # merging data into frame

    response = api.wsapi(ctx, frame)
    if response is None:
        ctx.echo(format_output(ctx, []))
        return

    ctx.echo(format_output(ctx, [response]))
