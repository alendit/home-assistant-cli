"""Tests for bundled Codex skill management."""

from pathlib import Path

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_skill_list() -> None:
    """List bundled skills."""
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["skill", "list"], catch_exceptions=False)

    assert result.exit_code == 0
    assert result.output == "home-assistant-manager\n"


def test_skill_install(tmp_path: Path) -> None:
    """Install the bundled skill into a target directory."""
    runner = CliRunner()
    target_dir = tmp_path / "skills"

    result = runner.invoke(
        cli.cli,
        ["skill", "install", "--target-dir", str(target_dir)],
        catch_exceptions=False,
    )

    installed_skill = target_dir / "home-assistant-manager"

    assert result.exit_code == 0
    assert installed_skill.is_dir()
    assert (installed_skill / "SKILL.md").is_file()
    assert "Home Assistant Manager" in (installed_skill / "SKILL.md").read_text()


def test_skill_install_requires_force_for_existing_target(tmp_path: Path) -> None:
    """Avoid overwriting an existing skill without explicit force."""
    runner = CliRunner()
    target_dir = tmp_path / "skills"
    existing_skill = target_dir / "home-assistant-manager"
    existing_skill.mkdir(parents=True)
    (existing_skill / "SKILL.md").write_text("customized")

    result = runner.invoke(
        cli.cli,
        ["skill", "install", "--target-dir", str(target_dir)],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert (existing_skill / "SKILL.md").read_text() == "customized"


def test_skill_install_force_replaces_existing_target(tmp_path: Path) -> None:
    """Replace an existing skill directory when force is enabled."""
    runner = CliRunner()
    target_dir = tmp_path / "skills"
    existing_skill = target_dir / "home-assistant-manager"
    existing_skill.mkdir(parents=True)
    (existing_skill / "SKILL.md").write_text("customized")

    result = runner.invoke(
        cli.cli,
        ["skill", "install", "--target-dir", str(target_dir), "--force"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "customized" not in (existing_skill / "SKILL.md").read_text()
