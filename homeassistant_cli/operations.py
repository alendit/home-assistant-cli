"""Shared command semantics for the CLI and the Python client."""

import json as json_
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import requests

from homeassistant_cli.config import Configuration
from homeassistant_cli.helper import to_attributes
import homeassistant_cli.remote as api

_TIMESTAMP_OFFSET_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+\d{2}:\d{2}$"
)


def list_states(ctx: Configuration, entityfilter: str = ".*") -> List[Dict[str, Any]]:
    """Return state rows filtered by entity id."""
    states = api.get_states(ctx)
    if entityfilter == ".*":
        return states

    entity_filter_re = re.compile(entityfilter)
    return [entity for entity in states if entity_filter_re.search(entity["entity_id"])]


def edit_state(
    ctx: Configuration,
    entity: str,
    newstate: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    merge: bool = False,
    json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update state without the CLI's interactive editor workflow."""
    if json is not None:
        if not isinstance(json, dict):
            raise ValueError("State payload must be a JSON object.")
        payload = dict(json)
        return api.set_state(ctx, entity, payload)

    if newstate is None and attributes is None:
        raise ValueError(
            "State edit in the Python client requires newstate, attributes, or json."
        )

    wanted_state: Dict[str, Any] = {}
    existing_state = api.get_state(ctx, entity)
    if existing_state and merge:
        wanted_state = dict(existing_state)

    if attributes:
        new_attr = dict(wanted_state.get("attributes", {}))
        new_attr.update(attributes)
        wanted_state["attributes"] = new_attr

    if newstate is not None:
        wanted_state["state"] = newstate
    else:
        if not existing_state:
            raise ValueError("No new or existing state provided.")
        wanted_state["state"] = existing_state["state"]

    return api.set_state(ctx, entity, wanted_state)


def toggle_states(
    ctx: Configuration,
    entities: tuple[str, ...],
) -> List[Dict[str, Any]]:
    """Toggle one or more entities."""
    return _call_homeassistant_service(ctx, entities, "toggle")


def turn_on_states(
    ctx: Configuration,
    entities: tuple[str, ...],
) -> List[Dict[str, Any]]:
    """Turn on one or more entities."""
    return _call_homeassistant_service(ctx, entities, "turn_on")


def turn_off_states(
    ctx: Configuration,
    entities: tuple[str, ...],
) -> List[Dict[str, Any]]:
    """Turn off one or more entities."""
    return _call_homeassistant_service(ctx, entities, "turn_off")


def _call_homeassistant_service(
    ctx: Configuration,
    entities: tuple[str, ...],
    command: str,
) -> List[Dict[str, Any]]:
    """Run a Home Assistant domain service for one or more entities."""
    return api.call_service(
        ctx,
        "homeassistant",
        command,
        {"entity_id": entities},
    )


def list_services(
    ctx: Configuration,
    servicefilter: str = ".*",
) -> List[Dict[str, Any]]:
    """Return flattened service rows filtered by name."""
    services = api.get_services(ctx)
    result = services
    if servicefilter != ".*":
        service_filter_re = re.compile(servicefilter)
        domains: List[Dict[str, Any]] = []
        for domain in services:
            domain_name = domain["domain"]
            service_data: Dict[str, Any] = {}
            for service_name, metadata in domain["services"].items():
                if service_filter_re.search(f"{domain_name}.{service_name}"):
                    service_data[service_name] = metadata

            if service_data:
                domains.append({"domain": domain_name, "services": service_data})
        result = domains

    flattened: List[Dict[str, Any]] = []
    for domain in result:
        for service_name, metadata in domain["services"].items():
            item = {"domain": domain["domain"], "service": service_name}
            item = {**item, **metadata}
            flattened.append(item)

    return flattened


def call_named_service(
    ctx: Configuration,
    service: str,
    arguments: Optional[Dict[str, Any]] = None,
    return_response: bool = False,
) -> List[Dict[str, Any]]:
    """Call a service using <domain>.<service> naming."""
    domain, service_name = split_service_name(service)
    if arguments is not None and not isinstance(arguments, dict):
        raise ValueError("Service payload must be a JSON object.")

    return api.call_service(
        ctx,
        domain,
        service_name,
        arguments or {},
        return_response=return_response,
    )


def split_service_name(service: str) -> tuple[str, str]:
    """Split a service name into its domain and service parts."""
    parts = service.split(".")
    if len(parts) != 2:
        raise ValueError("Service name must follow <domain>.<service> format.")
    return parts[0], parts[1]


def parse_service_arguments(arguments: str) -> Dict[str, Any]:
    """Parse CLI shorthand service arguments into a structured payload."""
    return to_attributes(arguments)


def normalize_raw_method(method: str) -> str:
    """Normalize raw REST methods to the Home Assistant API namespace."""
    if method.startswith("/api/"):
        return normalize_query_timestamps(method)

    if method.startswith("api/"):
        return normalize_query_timestamps(f"/{method}")

    if method.startswith("/"):
        return normalize_query_timestamps(method)

    return normalize_query_timestamps(f"/api/{method}")


def normalize_query_timestamps(method: str) -> str:
    """Percent-encode literal timezone offsets inside query values."""
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


def raw_get(
    ctx: Configuration,
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Perform a raw GET request and return parsed content."""
    return _parse_raw_response(
        api.restapi(ctx, api.METH_GET, normalize_raw_method(method), params)
    )


def raw_post(
    ctx: Configuration,
    method: str,
    json: Optional[Any] = None,
) -> Any:
    """Perform a raw POST request and return parsed content."""
    return _parse_raw_response(
        api.restapi(ctx, api.METH_POST, normalize_raw_method(method), json)
    )


def raw_ws(
    ctx: Configuration,
    wstype: str,
    json: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Perform a raw websocket request and return the response frame."""
    if json is not None and not isinstance(json, dict):
        raise ValueError("Websocket payload must be a JSON object.")

    frame = {"type": wstype}
    if json:
        frame = {**frame, **json}
    return api.wsapi(ctx, frame)


def _parse_raw_response(response: requests.Response) -> Any:
    """Parse a raw REST response in the same way as the CLI."""
    response.raise_for_status()
    try:
        return response.json()
    except json_.decoder.JSONDecodeError:
        return response.text


def show_dashboard(
    ctx: Configuration,
    url_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a dashboard configuration."""
    return api.lovelace_get_config(ctx, url_path)


def save_dashboard(
    ctx: Configuration,
    config: Dict[str, Any],
    url_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a dashboard configuration and return a normalized payload."""
    if not isinstance(config, dict):
        raise ValueError("Dashboard config must be a JSON object.")

    api.lovelace_save_config(ctx, config, url_path)
    return {
        "saved": True,
        "url_path": url_path,
        "config": config,
    }
