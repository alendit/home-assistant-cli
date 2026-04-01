"""Bundled Codex skill management for Home Assistant CLI (hass-cli)."""

from pathlib import Path
from typing import Optional

import click

from homeassistant_cli.cli import pass_context
from homeassistant_cli.codex_skills import DEFAULT_BUNDLED_SKILL
from homeassistant_cli.codex_skills import bundled_skill_names
from homeassistant_cli.codex_skills import install_bundled_skill
from homeassistant_cli.config import Configuration


@click.group("skill")
@pass_context
def cli(ctx: Configuration) -> None:
    """Manage bundled Codex skills."""


@cli.command("list")
@pass_context
def list_skills(ctx: Configuration) -> None:
    """List bundled Codex skills."""
    for skill_name in bundled_skill_names():
        click.echo(skill_name)


@cli.command("install")
@click.argument(
    "skill_name",
    required=False,
    default=DEFAULT_BUNDLED_SKILL,
    type=click.Choice(bundled_skill_names()),
)
@click.option(
    "--target-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help=(
        "Install into this skills directory instead of "
        "$CODEX_HOME/skills or ~/.codex/skills."
    ),
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Replace an existing installed skill directory.",
)
@pass_context
def install_skill(
    ctx: Configuration,
    skill_name: str,
    target_dir: Optional[Path],
    force: bool,
) -> None:
    """Install a bundled Codex skill."""
    try:
        destination = install_bundled_skill(
            skill_name,
            target_dir=target_dir,
            force=force,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as err:
        raise click.ClickException(str(err)) from err

    click.echo(f"Installed {skill_name} to {destination}")
    click.echo("Restart Codex to load the new skill.")
