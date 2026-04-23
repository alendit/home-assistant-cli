"""conftest.py loads all fixtures found in fixtures/.

Each file are made available as follows:

Given a file named: `mydata.json`
it will be available as:

mydata_text - str with the raw text
mydata      - Dict with the content parsed from json
"""

import json
from pathlib import Path

import click_log.core as logcore
import pytest

FIXTURES_PATH = Path(__file__).parent / "fixtures"


logcore.basic_config()


@pytest.fixture(autouse=True)
def clear_home_assistant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent from the developer's shell configuration."""
    for name in (
        "HASS_SERVER",
        "HASS_TOKEN",
        "HASSIO_TOKEN",
        "HASS_PASSWORD",
        "HASS_CERT",
    ):
        monkeypatch.delenv(name, raising=False)


def generate_fixture(content: str):
    """Generate the individual fixtures."""
    pass  # pylint: disable=unnecessary-pass

    @pytest.fixture(scope="module")
    def my_fixture():
        return content

    return my_fixture


def _inject_fixture(name: str, someparam: str):
    globals()[name] = generate_fixture(someparam)


def _all_fixtures():
    for fixture_path in FIXTURES_PATH.iterdir():
        name = fixture_path.stem
        ext = fixture_path.suffix

        with fixture_path.open() as file:
            content = file.read()

        _inject_fixture(name + "_text", content)
        if ext == ".json":
            _inject_fixture(name, json.loads(content))


_all_fixtures()  # type: ignore
