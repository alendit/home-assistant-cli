"""
Basic API to access remote instance of Home Assistant.

If a connection error occurs while communicating with the API a
HomeAssistantCliError will be raised.
"""

import asyncio
import collections
from datetime import datetime
import enum
import json
import logging
from typing import Any, Callable, Dict, List, Optional, cast
from urllib.parse import quote, urlencode

import aiohttp
import requests

from homeassistant_cli.config import Configuration, resolve_server
from homeassistant_cli.exceptions import HomeAssistantCliError
import homeassistant_cli.hassconst as hass

_LOGGER = logging.getLogger(__name__)

# Copied from aiohttp.hdrs
CONTENT_TYPE = "Content-Type"
METH_DELETE = "DELETE"
METH_GET = "GET"
METH_POST = "POST"


class APIStatus(enum.Enum):
    """Representation of an API status."""

    OK = "ok"
    INVALID_PASSWORD = "invalid_password"
    CANNOT_CONNECT = "cannot_connect"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the state."""
        return self.value


def restapi(
    ctx: Configuration,
    method: str,
    path: str,
    data: Optional[Any] = None,
) -> requests.Response:
    """Make a call to the Home Assistant REST API."""
    if not ctx.session:
        ctx.session = requests.Session()
        ctx.session.verify = not ctx.insecure
        if ctx.cert:
            ctx.session.cert = ctx.cert

        _LOGGER.debug(
            "Session: verify(%s), cert(%s)",
            ctx.session.verify,
            ctx.session.cert,
        )

    headers = {CONTENT_TYPE: hass.CONTENT_TYPE_JSON}  # type: Dict[str, Any]

    if ctx.token:
        headers["Authorization"] = f"Bearer {ctx.token}"
    if ctx.password:
        headers["x-ha-access"] = ctx.password

    normalized_path = path if path.startswith("/") else f"/{path}"
    url = f"{resolve_server(ctx).rstrip('/')}{normalized_path}"
    request_kwargs: Dict[str, Any] = {
        "headers": headers,
        "timeout": ctx.timeout,
    }

    if data is not None:
        if method == METH_GET:
            request_kwargs["params"] = data
        else:
            request_kwargs["data"] = json.dumps(data, cls=JSONEncoder)

    try:
        return ctx.session.request(method, url, **request_kwargs)

    except requests.exceptions.Timeout as ex:
        error = (
            f"Timeout talking to {method} {url} after {ctx.timeout}s"
            f" ({type(ex).__name__})"
        )
        _LOGGER.exception(error)
        raise HomeAssistantCliError(error) from ex
    except requests.exceptions.RequestException as ex:
        raise HomeAssistantCliError(
            f"Error connecting to {method} {url}" f" ({type(ex).__name__})"
        ) from ex


def wsapi(
    ctx: Configuration,
    frame: Dict[str, Any],
    callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Make a call to Home Assistant using WS API.

    if callback provided will keep listening and call
    on every message.

    If no callback return data returned.
    """

    async def fetcher() -> Optional[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                resolve_server(ctx) + "/api/websocket",
                max_msg_size=16 * 1024 * 1024,
            ) as wsconn:
                authed = False
                request = dict(frame)
                request["id"] = 1

                while not authed:
                    msg = await wsconn.receive()
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        raise HomeAssistantCliError("Websocket connection error")
                    if msg.type == aiohttp.WSMsgType.CLOSED:
                        raise HomeAssistantCliError("Websocket connection closed")
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    auth_data = cast(Dict[str, Any], json.loads(msg.data))

                    if auth_data["type"] == "auth_required":
                        await wsconn.send_str(
                            json.dumps(
                                {
                                    "type": "auth",
                                    "access_token": ctx.token,
                                }
                            )
                        )
                    elif auth_data["type"] == "auth_ok":
                        authed = True
                    elif auth_data["type"] == "auth_invalid":
                        raise HomeAssistantCliError(auth_data.get("message"))

                await wsconn.send_str(json.dumps(request))

                while True:
                    msg = await wsconn.receive()
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        raise HomeAssistantCliError("Websocket connection error")
                    if msg.type == aiohttp.WSMsgType.CLOSED:
                        raise HomeAssistantCliError("Websocket connection closed")
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    response_data = cast(Dict[str, Any], json.loads(msg.data))

                    if response_data["type"] == "auth_invalid":
                        raise HomeAssistantCliError(response_data.get("message"))

                    if callback:
                        callback(response_data)
                        continue

                    if response_data["type"] == "result":
                        return response_data
        return None

    return asyncio.run(fetcher())


class JSONEncoder(json.JSONEncoder):
    """JSONEncoder that supports Home Assistant objects."""

    # pylint: disable=method-hidden
    def default(self, o: Any) -> Any:
        """Convert Home Assistant objects.

        Hand other objects to the original method.
        """
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        if hasattr(o, "as_dict"):
            return o.as_dict()

        return json.JSONEncoder.default(self, o)


def get_areas(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return all areas."""
    frame = {"type": hass.WS_TYPE_AREA_REGISTRY_LIST}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(List[Dict[str, Any]], response["result"])


def find_area(ctx: Configuration, id_or_name: str) -> Optional[Dict[str, str]]:
    """Find area first by id and if no match by name."""
    areas = get_areas(ctx)

    area = next((x for x in areas if x["area_id"] == id_or_name), None)
    if not area:
        area = next((x for x in areas if x["name"] == id_or_name), None)

    return area


def create_area(ctx: Configuration, name: str) -> Dict[str, Any]:
    """Create area."""
    frame = {"type": hass.WS_TYPE_AREA_REGISTRY_CREATE, "name": name}

    return cast(Dict[str, Any], wsapi(ctx, frame))


def delete_area(ctx: Configuration, area_id: str) -> Dict[str, Any]:
    """Delete area."""
    frame = {"type": hass.WS_TYPE_AREA_REGISTRY_DELETE, "area_id": area_id}

    return cast(Dict[str, Any], wsapi(ctx, frame))


def rename_area(ctx: Configuration, area_id: str, new_name: str) -> Dict[str, Any]:
    """Rename area."""
    frame = {
        "type": hass.WS_TYPE_AREA_REGISTRY_UPDATE,
        "area_id": area_id,
        "name": new_name,
    }

    return cast(Dict[str, Any], wsapi(ctx, frame))


def rename_entity(
    ctx: Configuration,
    entity_id: str,
    new_id: Optional[str],
    new_name: Optional[str],
) -> Dict[str, Any]:
    """Rename entity."""
    frame = {
        "type": hass.WS_TYPE_ENTITY_REGISTRY_UPDATE,
        "entity_id": entity_id,
    }

    if new_name:
        frame["name"] = new_name
    if new_id:
        frame["new_entity_id"] = new_id

    return cast(Dict[str, Any], wsapi(ctx, frame))


def rename_device(ctx: Configuration, device_id: str, new_name: str) -> Dict[str, Any]:
    """Rename device."""
    frame = {
        "type": hass.WS_TYPE_DEVICE_REGISTRY_UPDATE,
        "device_id": device_id,
        "name_by_user": new_name,
    }

    return cast(Dict[str, Any], wsapi(ctx, frame))


def assign_area(ctx: Configuration, device_id: str, area_id: str) -> Dict[str, Any]:
    """Assign area."""
    frame = {
        "type": hass.WS_TYPE_DEVICE_REGISTRY_UPDATE,
        "area_id": area_id,
        "device_id": device_id,
    }

    return cast(Dict[str, Any], wsapi(ctx, frame))


def assign_entity_area(
    ctx: Configuration, entity_id: str, area_id: str
) -> Dict[str, Any]:
    """Assign area to entity."""
    frame = {
        "type": hass.WS_TYPE_ENTITY_REGISTRY_UPDATE,
        "area_id": area_id,
        "entity_id": entity_id,
    }

    return cast(Dict[str, Any], wsapi(ctx, frame))


def get_health(ctx: Configuration) -> Dict[str, Any]:
    """Get system Health."""
    frame = {"type": "system_health/info"}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(Dict[str, Any], response["result"])


def energy_get_prefs(ctx: Configuration) -> Dict[str, Any]:
    """Return the configured Energy dashboard preferences."""
    frame = {"type": "energy/get_prefs"}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(Dict[str, Any], response["result"])


def energy_save_prefs(ctx: Configuration, prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Persist Energy dashboard preferences."""
    frame = {"type": "energy/save_prefs", **prefs}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(Dict[str, Any], response["result"])


def energy_validate(ctx: Configuration) -> Dict[str, Any]:
    """Validate the currently configured Energy dashboard preferences."""
    frame = {"type": "energy/validate"}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(Dict[str, Any], response["result"])


def lovelace_get_config(
    ctx: Configuration, url_path: Optional[str] = None
) -> Dict[str, Any]:
    """Return the Lovelace config for the default or a named dashboard."""
    frame: Dict[str, Any] = {"type": "lovelace/config"}
    if url_path:
        frame["url_path"] = url_path

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(Dict[str, Any], response["result"])


def lovelace_save_config(
    ctx: Configuration, config: Dict[str, Any], url_path: Optional[str] = None
) -> Any:
    """Persist the Lovelace config for the default or a named dashboard."""
    frame: Dict[str, Any] = {"type": "lovelace/config/save", "config": config}
    if url_path:
        frame["url_path"] = url_path

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return response.get("result")


def get_devices(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return all devices."""
    frame = {"type": hass.WS_TYPE_DEVICE_REGISTRY_LIST}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(List[Dict[str, Any]], response["result"])


def get_entities(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return all entities."""
    frame = {"type": hass.WS_TYPE_ENTITY_REGISTRY_LIST}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(List[Dict[str, Any]], response["result"])


def get_todo_items(ctx: Configuration, entity_id: str) -> List[Dict[str, Any]]:
    """Return all items for one to-do entity."""
    frame = {"type": "todo/item/list", "entity_id": entity_id}

    response = wsapi(ctx, frame)
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    result = response.get("result")
    if not isinstance(result, dict):
        raise HomeAssistantCliError("Unexpected response returned from todo/item/list")

    items = result.get("items")
    if not isinstance(items, list):
        raise HomeAssistantCliError("Unexpected items payload returned from to-do API")

    return cast(List[Dict[str, Any]], items)


def get_entity(ctx: Configuration, entity_id: str) -> Optional[Dict[str, Any]]:
    """Return entity registry details."""
    frame = {"type": hass.WS_TYPE_ENTITY_REGISTRY_GET, "entity_id": entity_id}

    response = wsapi(ctx, frame)
    if response is None:
        return None

    return cast(Optional[Dict[str, Any]], response.get("result"))


def validate_api(ctx: Configuration) -> APIStatus:
    """Make a call to validate API."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API)

        if req.status_code == 200:
            return APIStatus.OK

        if req.status_code == 401:
            return APIStatus.INVALID_PASSWORD

        return APIStatus.UNKNOWN

    except HomeAssistantCliError:
        return APIStatus.CANNOT_CONNECT


def get_info(ctx: Configuration) -> Dict[str, Any]:
    """Get basic info about the Home Assistant instance."""
    try:
        config = get_config(ctx)
    except ValueError as ex:
        raise HomeAssistantCliError(f"Unexpected error retrieving information: {ex}")

    return {
        "base_url": config.get("external_url")
        or config.get("internal_url")
        or resolve_server(ctx),
        "location_name": config.get("location_name"),
        "requires_api_password": False,
        "version": config.get("version"),
    }


def get_events(ctx: Configuration) -> Dict[str, Any]:
    """Return all events."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_EVENTS)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting events: {ex}")

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(f"Error while getting all events: {req.text}")


def get_history(
    ctx: Configuration,
    entities: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> List[List[Dict[str, Any]]]:
    """Return History."""
    try:
        if start_time:
            method = f"{hass.URL_API_HISTORY_PERIOD}/{quote(start_time.isoformat())}"
        else:
            method = hass.URL_API_HISTORY

        params = collections.OrderedDict()  # type: Dict[str, str]

        if entities:
            params["filter_entity_id"] = ",".join(entities)
        if end_time:
            params["end_time"] = end_time.isoformat()

        if params:
            method = f"{method}?{urlencode(params)}"

        req = restapi(ctx, METH_GET, method)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting history: {ex}")

    if req.status_code == 200:
        return cast(List[List[Dict[str, Any]]], req.json())

    raise HomeAssistantCliError(f"Error while getting all events: {req.text}")


def get_states(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return all states."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_STATES)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting state: {ex}")

    if req.status_code == 200:
        data = req.json()  # type: List[Dict[str, Any]]
        return data

    raise HomeAssistantCliError(f"Error while getting all states: {req.text}")


def get_raw_error_log(ctx: Configuration) -> str:
    """Return the error log."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_ERROR_LOG)
        req.raise_for_status()
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting error log: {ex}")

    return req.text


def get_config(ctx: Configuration) -> Dict[str, Any]:
    """Return the running configuration."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_CONFIG)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting configuration: {ex}")

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(f"Error while getting all configuration: {req.text}")


def get_config_entries(ctx: Configuration) -> List[Dict[str, Any]]:
    """Return all config entries."""
    response = wsapi(ctx, {"type": "config_entries/get"})
    if response is None:
        raise HomeAssistantCliError("No response returned from websocket API")

    return cast(List[Dict[str, Any]], response["result"])


def get_config_entry(ctx: Configuration, entry_id: str) -> Optional[Dict[str, Any]]:
    """Return a single config entry by id."""
    return next(
        (
            entry
            for entry in get_config_entries(ctx)
            if entry.get("entry_id") == entry_id
        ),
        None,
    )


def get_config_entry_diagnostics(ctx: Configuration, entry_id: str) -> Dict[str, Any]:
    """Return diagnostics for one config entry."""
    path = f"/api/diagnostics/config_entry/{quote(entry_id, safe='')}"
    try:
        req = restapi(ctx, METH_GET, path)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error getting diagnostics for config entry {entry_id}: {ex}"
        )

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(
        f"Error while getting diagnostics for config entry {entry_id}: {req.text}"
    )


def get_config_entry_flow_handlers(ctx: Configuration) -> List[str]:
    """Return available config-entry flow handlers."""
    path = "/api/config/config_entries/flow_handlers"
    try:
        req = restapi(ctx, METH_GET, path)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error getting config entry flow handlers: {ex}"
        )

    if req.status_code == 200:
        return cast(List[str], req.json())

    raise HomeAssistantCliError(
        f"Error while getting config entry flow handlers: {req.text}"
    )


def init_config_entry_flow(
    ctx: Configuration, handler: str, show_advanced_options: bool = False
) -> Dict[str, Any]:
    """Start a config-entry flow."""
    path = "/api/config/config_entries/flow"
    data = {
        "handler": handler,
        "show_advanced_options": show_advanced_options,
    }
    try:
        req = restapi(ctx, METH_POST, path, data)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error starting config entry flow for {handler}: {ex}"
        )

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(
        f"Error while starting config entry flow for {handler}: {req.text}"
    )


def continue_config_entry_flow(
    ctx: Configuration, flow_id: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Continue a config-entry flow."""
    path = f"/api/config/config_entries/flow/{flow_id}"
    try:
        req = restapi(ctx, METH_POST, path, data or {})
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error continuing config entry flow {flow_id}: {ex}"
        )

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(
        f"Error while continuing config entry flow {flow_id}: {req.text}"
    )


def get_collection_item_config(
    ctx: Configuration, collection: str, item_id: str
) -> Dict[str, Any]:
    """Return stored configuration for a collection item."""
    path = f"/api/config/{collection}/config/{item_id}"
    try:
        req = restapi(ctx, METH_GET, path)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error getting {collection} config: {ex}"
        )

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(f"Error while getting {collection} config: {req.text}")


def update_collection_item_config(
    ctx: Configuration,
    collection: str,
    item_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update stored configuration for a collection item."""
    path = f"/api/config/{collection}/config/{item_id}"
    try:
        req = restapi(ctx, METH_POST, path, data)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(
            f"Unexpected error updating {collection} config: {ex}"
        )

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())

    raise HomeAssistantCliError(f"Error while updating {collection} config: {req.text}")


def get_state(ctx: Configuration, entity_id: str) -> Optional[Dict[str, Any]]:
    """Get entity state. If ok, return dictionary with state.

    If no entity found return None - otherwise excepton raised
    with details.
    """
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_STATES_ENTITY.format(entity_id))
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting state: {ex}")

    if req.status_code == 200:
        return cast(Dict[str, Any], req.json())
    if req.status_code == 404:
        return None

    raise HomeAssistantCliError(f"Error while getting Entity {entity_id}: {req.text}")


def remove_state(ctx: Configuration, entity_id: str) -> bool:
    """Call API to remove state for entity_id.

    If success return True, if could not find the entity return False.
    Otherwise raise exception with details.
    """
    try:
        req = restapi(ctx, METH_DELETE, hass.URL_API_STATES_ENTITY.format(entity_id))

        if req.status_code == 200:
            return True
        if req.status_code == 404:
            return False
    except HomeAssistantCliError:
        raise HomeAssistantCliError("Unexpected error removing state")

    raise HomeAssistantCliError(f"Error removing state: {req.status_code} - {req.text}")


def set_state(
    ctx: Configuration, entity_id: str, data: Dict[str, Any]
) -> Dict[str, Any]:
    """Set/update state for entity id."""
    try:
        req = restapi(
            ctx, METH_POST, hass.URL_API_STATES_ENTITY.format(entity_id), data
        )
    except HomeAssistantCliError as exception:
        raise HomeAssistantCliError(
            "Error updating state for entity {}: {}".format(entity_id, exception)
        )

    if req.status_code not in (200, 201):
        raise HomeAssistantCliError(
            "Error changing state for entity {}: {} - {}".format(
                entity_id, req.status_code, req.text
            )
        )
    return cast(Dict[str, Any], req.json())


def render_template(
    ctx: Configuration, template: str, variables: Dict[str, Any]
) -> str:
    """Render template."""
    data = {"template": template, "variables": variables}

    try:
        req = restapi(ctx, METH_POST, hass.URL_API_TEMPLATE, data)
    except HomeAssistantCliError as exception:
        raise HomeAssistantCliError(f"Error applying template: {exception}")

    if req.status_code not in (200, 201):
        raise HomeAssistantCliError(
            "Error applying template: {} - {}".format(req.status_code, req.text)
        )
    return req.text


def get_event_listeners(ctx: Configuration) -> Dict[str, Any]:
    """List of events that is being listened for."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_EVENTS)
        if req.status_code == 200:
            return cast(Dict[str, Any], req.json())
        return {}

    except (HomeAssistantCliError, ValueError):
        # ValueError if req.json() can't parse the json
        _LOGGER.exception("Unexpected result retrieving event listeners")

        return {}


def fire_event(
    ctx: Configuration, event_type: str, data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Fire an event at remote API."""
    try:
        req = restapi(
            ctx, METH_POST, hass.URL_API_EVENTS_EVENT.format(event_type), data
        )

        if req.status_code != 200:
            _LOGGER.error("Error firing event: %d - %s", req.status_code, req.text)

        return cast(Dict[str, Any], req.json())

    except HomeAssistantCliError as exception:
        raise HomeAssistantCliError(f"Error firing event: {exception}")


def call_service(
    ctx: Configuration,
    domain: str,
    service: str,
    service_data: Optional[Dict[str, Any]] = None,
    return_response: bool = False,
) -> List[Dict[str, Any]]:
    """Call a service."""
    url = hass.URL_API_SERVICES_SERVICE.format(domain, service)
    if return_response:
        url = f"{url}?return_response=true"

    try:
        req = restapi(
            ctx,
            METH_POST,
            url,
            service_data,
        )
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Error calling service: {ex}")

    if req.status_code != 200:
        raise HomeAssistantCliError(
            f"Error calling service: {req.status_code} - {req.text}"
        )

    return cast(List[Dict[str, Any]], req.json())


def get_services(
    ctx: Configuration,
) -> List[Dict[str, Any]]:
    """Get list of services."""
    try:
        req = restapi(ctx, METH_GET, hass.URL_API_SERVICES)
    except HomeAssistantCliError as ex:
        raise HomeAssistantCliError(f"Unexpected error getting services: {ex}")

    if req.status_code == 200:
        return cast(List[Dict[str, Any]], req.json())

    raise HomeAssistantCliError(f"Error while getting all services: {req.text}")
