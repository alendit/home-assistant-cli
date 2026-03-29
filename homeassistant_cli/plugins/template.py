"""Template plugin for Home Assistant CLI (hass-cli)."""

import logging
import os
from typing import Any, Dict, Optional, TextIO

import click
from jinja2 import Environment, FileSystemLoader

from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)


def render(template_path: str, data: Dict[str, Any], strict: bool = False) -> str:
    """Render template."""
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_path)),
        keep_trailing_newline=True,
    )
    if strict:
        from jinja2 import StrictUndefined

        env.undefined = StrictUndefined

    # Add environ global
    env.globals["environ"] = os.environ.get

    output = env.get_template(os.path.basename(template_path)).render(data)
    return output


@click.command("template")
@click.argument("template", required=True, type=click.File())
@click.argument("datafile", type=click.File(), required=False)
@click.option(
    "--local",
    default=False,
    is_flag=True,
    help="If should render template locally.",
)
@pass_context
def cli(
    ctx: Configuration,
    template: TextIO,
    datafile: Optional[TextIO],
    local: bool,
) -> None:
    """Render templates on server or locally.

    TEMPLATE - jinja2 template file
    DATAFILE - YAML file with variables to pass to rendering
    """
    variables = {}  # type: Dict[str, Any]
    if datafile:
        variables = ctx.yamlload(datafile.read())

    templatestr = template.read()

    _LOGGING.debug("Rendering: %s Variables: %s", templatestr, variables)

    if local:
        output = render(template.name, variables, True)
    else:
        output = api.render_template(ctx, templatestr, variables)

    ctx.echo(output)
