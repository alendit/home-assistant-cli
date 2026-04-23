"""Public Python client that mirrors the hass-cli command surface."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from homeassistant_cli.config import build_configuration
from homeassistant_cli.config import Configuration
from homeassistant_cli.config import UNSET
import homeassistant_cli.operations as operations
import homeassistant_cli.remote as api


class StateNamespace:
    """Python client accessors for the `state` command group."""

    def __init__(self, ctx: Configuration) -> None:
        """Store the shared client configuration."""
        self._ctx = ctx

    def get(self, entity: str) -> Optional[Dict[str, Any]]:
        """Return one entity state, or None when it does not exist."""
        return api.get_state(self._ctx, entity)

    def list(self, entityfilter: str = ".*") -> List[Dict[str, Any]]:
        """Return states filtered by entity id."""
        return operations.list_states(self._ctx, entityfilter)

    def delete(self, entity: str) -> bool:
        """Delete one entity state."""
        return api.remove_state(self._ctx, entity)

    def edit(
        self,
        entity: str,
        newstate: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        merge: bool = False,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update one entity state without the interactive editor flow."""
        return operations.edit_state(
            self._ctx,
            entity,
            newstate=newstate,
            attributes=attributes,
            merge=merge,
            json=json,
        )

    def toggle(self, *entities: str) -> List[Dict[str, Any]]:
        """Toggle one or more entities."""
        return operations.toggle_states(self._ctx, entities)

    def turn_on(self, *entities: str) -> List[Dict[str, Any]]:
        """Turn on one or more entities."""
        return operations.turn_on_states(self._ctx, entities)

    def turn_off(self, *entities: str) -> List[Dict[str, Any]]:
        """Turn off one or more entities."""
        return operations.turn_off_states(self._ctx, entities)


class ServiceNamespace:
    """Python client accessors for the `service` command group."""

    def __init__(self, ctx: Configuration) -> None:
        """Store the shared client configuration."""
        self._ctx = ctx

    def list(self, servicefilter: str = ".*") -> List[Dict[str, Any]]:
        """Return flattened service rows."""
        return operations.list_services(self._ctx, servicefilter)

    def call(
        self,
        service: str,
        arguments: Optional[Dict[str, Any]] = None,
        return_response: bool = False,
    ) -> List[Dict[str, Any]]:
        """Call one Home Assistant service."""
        return operations.call_named_service(
            self._ctx,
            service,
            arguments=arguments,
            return_response=return_response,
        )


class RawNamespace:
    """Python client accessors for the `raw` command group."""

    def __init__(self, ctx: Configuration) -> None:
        """Store the shared client configuration."""
        self._ctx = ctx

    def get(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform a raw GET request."""
        return operations.raw_get(self._ctx, method, params)

    def post(self, method: str, json: Optional[Any] = None) -> Any:
        """Perform a raw POST request."""
        return operations.raw_post(self._ctx, method, json)

    def ws(
        self,
        wstype: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Perform a raw websocket request."""
        return operations.raw_ws(self._ctx, wstype, json)


class DashboardNamespace:
    """Python client accessors for the `dashboard` command group."""

    def __init__(self, ctx: Configuration) -> None:
        """Store the shared client configuration."""
        self._ctx = ctx

    def show(self, url_path: Optional[str] = None) -> Dict[str, Any]:
        """Return one dashboard configuration."""
        return operations.show_dashboard(self._ctx, url_path)

    def save(
        self,
        config: Dict[str, Any],
        url_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save one dashboard configuration."""
        return operations.save_dashboard(self._ctx, config, url_path)


class HassClient:
    """Synchronous Python facade that mirrors representative hass-cli groups."""

    _ctx: Configuration

    def __init__(
        self,
        server: object = UNSET,
        token: object = UNSET,
        password: object = UNSET,
        timeout: object = UNSET,
        cert: object = UNSET,
        insecure: bool = False,
    ) -> None:
        """Build a client using explicit args first, then CLI-style env defaults."""
        self._ctx = build_configuration(
            server=server,
            token=token,
            password=password,
            timeout=timeout,
            cert=cert,
            insecure=insecure,
        )
        self.state = StateNamespace(self._ctx)
        self.service = ServiceNamespace(self._ctx)
        self.raw = RawNamespace(self._ctx)
        self.dashboard = DashboardNamespace(self._ctx)
