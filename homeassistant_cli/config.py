"""Configuration for Home Assistant CLI (hass-cli)."""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, cast

import click
from requests import Session
from ruamel.yaml import YAML
import zeroconf

import homeassistant_cli.const as const
import homeassistant_cli.yaml as yaml

_LOGGING = logging.getLogger(__name__)
UNSET = object()


class _ZeroconfListener(zeroconf.ServiceListener):
    """Representation of the Zeroconf listener."""

    def __init__(self) -> None:
        """Initialize the listener."""
        self.services: Dict[str, Optional[zeroconf.ServiceInfo]] = {}

    def remove_service(
        self, _zeroconf: zeroconf.Zeroconf, _type: str, name: str
    ) -> None:
        """Remove service."""
        self.services[name] = None

    def add_service(self, _zeroconf: zeroconf.Zeroconf, _type: str, name: str) -> None:
        """Add service."""
        self.services[name] = _zeroconf.get_service_info(_type, name)

    def update_service(
        self, _zeroconf: zeroconf.Zeroconf, _type: str, name: str
    ) -> None:
        """Update service details when Zeroconf notifies about changes."""
        self.services[name] = _zeroconf.get_service_info(_type, name)


def _locate_ha() -> Optional[str]:
    """Locate the Home Assistant instance."""
    _zeroconf = zeroconf.Zeroconf()
    listener = _ZeroconfListener()
    zeroconf.ServiceBrowser(_zeroconf, "_home-assistant._tcp.local.", listener)
    try:
        import time

        retries = 0
        while not listener.services and retries < 5:
            _LOGGING.info("Trying to locate Home Assistant on local network...")
            time.sleep(0.5)
            retries = retries + 1
    finally:
        _zeroconf.close()

    if listener.services:
        if len(listener.services) > 1:
            _LOGGING.warning(
                "Found multiple Home Assistant instances at %s",
                ", ".join(listener.services),
            )
            _LOGGING.warning("Use --server to explicitly specify one.")
            return None

        _, service = listener.services.popitem()
        if service is None:
            _LOGGING.warning("Found Home Assistant service without details")
            return None

        base_url_bytes = service.properties.get(b"base_url")
        if base_url_bytes is None:
            _LOGGING.warning("Found Home Assistant service without base_url")
            return None

        base_url = base_url_bytes.decode("utf-8")
        _LOGGING.info("Found and using %s as server", base_url)
        return base_url

    _LOGGING.warning("Found no Home Assistant on local network. Using defaults")
    return None


def resolve_server(ctx: Any) -> str:
    """Resolve server if not already done.

    if server is `auto` try and resolve it
    """
    # to work around bug in click that hands out
    # non-Configuration context objects.
    if not hasattr(ctx, "resolved_server"):
        ctx.resolved_server = None

    if not ctx.resolved_server:

        if ctx.server == "auto":

            if "HASSIO_TOKEN" in os.environ and "HASS_TOKEN" not in os.environ:
                ctx.resolved_server = const.DEFAULT_SERVER_MDNS
            else:
                if not ctx.resolved_server and "pytest" in sys.modules:
                    ctx.resolved_server = const.DEFAULT_SERVER
                else:
                    ctx.resolved_server = _locate_ha()
                    if not ctx.resolved_server:
                        sys.exit(3)
        else:
            ctx.resolved_server = ctx.server

        if not ctx.resolved_server:
            ctx.resolved_server = const.DEFAULT_SERVER

    return cast(str, ctx.resolved_server)


def default_token() -> Optional[str]:
    """Return the configured access token from the environment."""
    return os.environ.get("HASS_TOKEN", os.environ.get("HASSIO_TOKEN"))


def build_configuration(
    server: Any = UNSET,
    token: Any = UNSET,
    password: Any = UNSET,
    timeout: Any = UNSET,
    cert: Any = UNSET,
    insecure: bool = False,
) -> "Configuration":
    """Build a configuration using the same env/default behavior as the CLI."""
    ctx = Configuration()
    ctx.server = (
        os.environ.get("HASS_SERVER", const.AUTO_SERVER)
        if server is UNSET
        else cast(str, server or const.AUTO_SERVER)
    )
    ctx.token = default_token() if token is UNSET else cast(Optional[str], token)
    ctx.password = (
        os.environ.get("HASS_PASSWORD")
        if password is UNSET
        else cast(Optional[str], password)
    )
    ctx.timeout = (
        const.DEFAULT_TIMEOUT
        if timeout is UNSET or timeout is None
        else cast(int, timeout)
    )
    ctx.cert = (
        os.environ.get("HASS_CERT") if cert is UNSET else cast(Optional[str], cert)
    )
    ctx.insecure = insecure
    return ctx


class Configuration:
    """The configuration context for the Home Assistant CLI."""

    def __init__(self) -> None:
        """Initialize the configuration."""
        self.verbose: bool = False
        self.server: str = const.AUTO_SERVER
        self.resolved_server: Optional[str] = None
        self.output: str = const.DEFAULT_OUTPUT
        self.token: Optional[str] = None
        self.password: Optional[str] = None
        self.insecure: bool = False
        self.timeout: int = const.DEFAULT_TIMEOUT
        self.debug: bool = False
        self.showexceptions: bool = False
        self.session: Optional[Session] = None
        self.cert: Optional[str] = None
        self.columns: Optional[List[Tuple[str, ...]]] = None
        self.no_headers: bool = False
        self.table_format: str = "plain"
        self.sort_by: Optional[str] = None

    def echo(self, msg: str, *args: Optional[Any]) -> None:
        """Put content message to stdout."""
        self.log(msg, *args)

    def log(  # pylint: disable=no-self-use
        self, msg: str, *args: Optional[str]
    ) -> None:  # pylint: disable=no-self-use
        """Log a message to stdout."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stdout)

    def vlog(self, msg: str, *args: Optional[str]) -> None:
        """Log a message only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def __repr__(self) -> str:
        """Return the representation of the Configuration."""
        view = {
            "server": self.server,
            "access-token": "yes" if self.token is not None else "no",
            "api-password": "yes" if self.password is not None else "no",
            "insecure": self.insecure,
            "output": self.output,
            "verbose": self.verbose,
        }

        return f"<Configuration({view})"

    def resolve_server(self) -> str:
        """Return resolved server (after resolving if needed)."""
        return resolve_server(self)

    def auto_output(self, auto_output: str) -> str:
        """Configure output format."""
        if self.output == "auto":
            if auto_output == "data":
                auto_output = const.DEFAULT_DATAOUTPUT
            _LOGGING.debug("Setting auto-output to: %s", auto_output)
            self.output = auto_output
        return self.output

    def yaml(self) -> YAML:
        """Create default yaml parser."""
        if self:
            yaml.yaml()
        return yaml.yaml()

    def yamlload(self, source: str) -> Any:
        """Load YAML from source."""
        return self.yaml().load(source)

    def yamldump(self, source: Any) -> str:
        """Dump dictionary to YAML string."""
        return cast(str, yaml.dumpyaml(self.yaml(), source))
