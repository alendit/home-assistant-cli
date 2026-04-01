"""Helpers for bundled Codex skill installation."""

import os
import shutil
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_BUNDLED_SKILL = "home-assistant-manager"

_BUNDLED_SKILLS: Dict[str, str] = {
    DEFAULT_BUNDLED_SKILL: "home_assistant_manager",
}


def bundled_skill_names() -> List[str]:
    """Return bundled skill names in a stable order."""
    return sorted(_BUNDLED_SKILLS)


def default_skills_directory() -> Path:
    """Return the default Codex skills directory."""
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def install_bundled_skill(
    skill_name: str,
    target_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    """Install a bundled skill into the requested destination."""
    source = _skill_resource(skill_name)
    destination_root = (
        target_dir.expanduser()
        if target_dir is not None
        else default_skills_directory()
    )
    destination = destination_root / skill_name

    if destination.exists():
        if not force:
            raise FileExistsError(
                f"Skill already exists at {destination}; use --force to replace it."
            )
        _remove_path(destination)

    _copy_resource_tree(source, destination)
    return destination


def _skill_resource(skill_name: str) -> Traversable:
    """Resolve a bundled skill resource tree."""
    try:
        skill_dir = _BUNDLED_SKILLS[skill_name]
    except KeyError as err:
        raise ValueError(f"Unknown bundled skill: {skill_name}") from err

    source = resources.files("homeassistant_cli.skills").joinpath(skill_dir)
    if not source.is_dir():
        raise FileNotFoundError(
            f"Bundled skill {skill_name} is missing from the package."
        )
    return source


def _copy_resource_tree(source: Traversable, destination: Path) -> None:
    """Copy a packaged resource directory into a filesystem destination."""
    destination.mkdir(parents=True, exist_ok=True)

    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            _copy_resource_tree(entry, target)
        else:
            target.write_bytes(entry.read_bytes())


def _remove_path(path: Path) -> None:
    """Remove a file or directory before reinstalling a skill."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
