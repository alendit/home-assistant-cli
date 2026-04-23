"""Helpers for bundled Codex skill installation."""

import os
import shutil
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_BUNDLED_SKILL = "home-assistant-manager"

_BUNDLED_SKILLS: Dict[str, str] = {
    DEFAULT_BUNDLED_SKILL: "skills/home-assistant-manager",
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
    source = _skill_path(skill_name)
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


def _skill_path(skill_name: str) -> Path:
    """Resolve a bundled skill resource tree from the source checkout or package."""
    try:
        skill_path = Path(_BUNDLED_SKILLS[skill_name])
    except KeyError as err:
        raise ValueError(f"Unknown bundled skill: {skill_name}") from err

    source = _source_checkout_root() / skill_path
    if source.is_dir():
        return source

    source = _installed_skill_path(skill_name, skill_path)
    if source.is_dir():
        return source

    raise FileNotFoundError(f"Bundled skill {skill_name} is missing from the package.")


def _source_checkout_root() -> Path:
    """Return the repository root when running from a source checkout."""
    return Path(__file__).resolve().parent.parent


def _installed_skill_path(skill_name: str, skill_path: Path) -> Path:
    """Return the installed package path for a packaged skill."""
    try:
        distribution = metadata.distribution("homeassistant-cli")
    except metadata.PackageNotFoundError:
        return Path()

    skill_marker = skill_path / "SKILL.md"
    for package_path in distribution.files or []:
        if Path(package_path.as_posix()) == skill_marker:
            return Path(package_path.locate()).parent

    raise FileNotFoundError(f"Bundled skill {skill_name} is missing from the package.")


def _copy_resource_tree(source: Path, destination: Path) -> None:
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
