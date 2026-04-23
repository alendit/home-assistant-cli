# Home Assistant CLI

[![CI](https://github.com/alendit/home-assistant-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/alendit/home-assistant-cli/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/alendit/home-assistant-cli)](LICENSE.md)

`hass-cli` is a command-line client for Home Assistant. It can inspect runtime
state, call services, work with registry objects such as devices and areas, and
manage stored configuration for automations and scripts. The package also
exports a synchronous Python client for scripting and agent use:
`from homeassistant_cli import HassClient`.

It works against local and remote Home Assistant instances and supports JSON,
YAML, tabular output, and shell completion.

## Installation

`homeassistant-cli` supports Python 3.11 and newer. The repository defaults to
Python 3.14 for local development and CI.

This fork lives at [alendit/home-assistant-cli](https://github.com/alendit/home-assistant-cli).

Install the current development branch of `hass-cli` directly from this fork,
then install the bundled `home-assistant-manager` skill:

```bash
uv tool install git+https://github.com/alendit/home-assistant-cli@main
hass-cli skill install
```

That installs the bundled skill into `$CODEX_HOME/skills` or
`~/.codex/skills`. Restart Codex after installation so the new skill is loaded.

If you only want the skill without installing `hass-cli`, install it from this
fork with `npx skills add`:

```bash
npx skills add https://github.com/alendit/home-assistant-cli --skill home-assistant-manager
```

Run the local checkout with `uv`:

```bash
uv sync
uv run hass-cli --help
uv run hass-cli skill install --target-dir ~/.codex/skills
```

If you want to import the Python client from a local checkout:

```bash
uv sync
uv run python -c "from homeassistant_cli import HassClient; print(HassClient)"
```

Community packages are also available in several ecosystems, including Fedora,
Homebrew, and Nixpkgs. Those packages may lag behind the latest release.

## Setup

Create a long-lived access token in your Home Assistant profile, then point
`hass-cli` or `HassClient` at your instance with either explicit parameters or
environment variables.

```bash
export HASS_SERVER="https://homeassistant.local:8123"
export HASS_TOKEN="<long-lived-access-token>"
```

You can also use:

- `HASS_PASSWORD` for legacy API password setups
- `HASSIO_TOKEN` as a fallback token source when `HASS_TOKEN` is unset
- `HASS_CERT` for a client certificate
- `--cert` for a client certificate
- `--insecure` for self-signed TLS during local testing

If your instance is reachable through discovery, `--server auto` is the default.
`HassClient()` follows the same env/default precedence as the CLI when
constructor arguments are omitted.

## Quick Start

Basic connectivity:

```bash
hass-cli info
hass-cli config release
hass-cli config components
```

Inspect runtime state:

```bash
hass-cli state list
hass-cli state get sun.sun
hass-cli state history --since 30m light.kitchen_light
hass-cli history summary --since 7d sensor.bedroom_temperature
hass-cli history average --since 7d sensor.bedroom_temperature
```

Call services:

```bash
hass-cli service list light
hass-cli service call light.turn_on --arguments entity_id=light.kitchen,brightness=180
hass-cli service call light.turn_on --json '{"entity_id":"light.kitchen","brightness":180}'
```

Inspect raw API endpoints:

```bash
hass-cli raw get config
hass-cli raw get /api/config
hass-cli raw post services/light/turn_on --json '{"entity_id":"light.kitchen"}'
```

When developing against this repository, prefer the checked-out code:

```bash
uv run hass-cli info
```

## Python Client

Use `HassClient` when you want the same Home Assistant interface without shell
wrapping. The client is synchronous and mirrors representative CLI groups while
returning Python dict/list data instead of formatted text.

Constructor options:

- `server`
- `token`
- `password`
- `timeout`
- `cert`
- `insecure`

If you omit those arguments, `HassClient()` reads the same defaults as the CLI:
`HASS_SERVER`, `HASS_TOKEN`, `HASSIO_TOKEN`, `HASS_PASSWORD`, and `HASS_CERT`.
Explicit constructor args always win over env vars.

Basic usage:

```python
from homeassistant_cli import HassClient

client = HassClient()

info = client.raw.get("config")
state = client.state.get("sun.sun")
states = client.state.list(r"light\.")
client.service.call(
    "light.turn_on",
    arguments={"entity_id": "light.kitchen", "brightness": 180},
)
dashboard = client.dashboard.show("dashboard-electricity")
```

Current Python namespaces:

- `client.state`: `get`, `list`, `delete`, `edit`, `toggle`, `turn_on`, `turn_off`
- `client.service`: `list`, `call`
- `client.raw`: `get`, `post`, `ws`
- `client.dashboard`: `show`, `save`

Python API notes:

- return values are structured Python data, not CLI-formatted strings
- invalid library usage raises normal Python exceptions instead of exiting
- `state.edit(...)` is non-interactive in Python; pass structured values instead
  of relying on the CLI editor flow

## Current Command Surface

### Core Runtime Commands

- `info`: basic server details
- `config`: configuration details, loaded components, release, whitelist dirs
- `state`: list, get, edit, delete, toggle, turn on/off, and read history
- `history`: fetch recorder history and compute time-weighted summaries
- `service`: list services and call a service
- `event`: interact with the event bus
- `template`: render templates locally or on the server
- `raw`: direct REST and websocket access for advanced workflows
- `config-entry`: inspect configured integrations and drive onboarding flows
- `pyscript`: reload pyscript files, generate stubs, and call pyscript services

### Typed Home Assistant Commands

These commands give you a more specific interface for common Home Assistant
objects instead of making you stitch everything together through `state`,
`service`, and `raw`.

#### Automations

```bash
hass-cli automation list
hass-cli automation find "lava|motion"
hass-cli automation show automation.kitchen_lights
hass-cli automation export automation.kitchen_lights
hass-cli automation patch automation.kitchen_lights --json '{"mode":"restart"}'
hass-cli automation trigger automation.kitchen_lights
hass-cli automation disable automation.kitchen_lights
hass-cli automation update automation.kitchen_lights --json '{"alias":"Kitchen Lights"}'
```

`automation export` returns the exact stored config payload accepted by
`automation update`. `automation show` adds runtime fields for operator context.
For smaller changes, prefer `automation patch` so you can keep the edit inline.
All automation config commands can resolve references from an entity ID, storage
ID, or friendly name.

#### Scripts

```bash
hass-cli script list
hass-cli script find bedtime
hass-cli script show script.goodnight
hass-cli script export script.goodnight
hass-cli script patch script.goodnight --json '{"mode":"queued"}'
hass-cli script run script.goodnight --arguments room=bedroom
hass-cli script run script.goodnight --json '{"room":"bedroom"}'
hass-cli script stop script.goodnight
```

#### Scenes

```bash
hass-cli scene list
hass-cli scene find evening
hass-cli scene show scene.evening
hass-cli scene activate scene.evening
```

#### Helpers

```bash
hass-cli helper list
hass-cli helper list --type timer
hass-cli helper find lava
hass-cli helper show timer.lava_lampe_timer
```

`helper` currently focuses on discovery across supported helper domains such as
timers and `input_*` helpers. Runtime control still happens through the normal
entity state and service APIs.

#### Config Entries

```bash
hass-cli config-entry list
hass-cli config-entry show 01KN34CRWDARH1TJYKQZX45VBY
hass-cli config-entry show 01KN34CRWDARH1TJYKQZX45VBY --with-data
hass-cli config-entry handlers
hass-cli config-entry init codex_app_server
hass-cli config-entry continue 01KN34CF2CERPBBNH8G8N4KQDB --json '{"bridge_url":"ws://127.0.0.1:4311"}'
hass-cli config-entry create codex_app_server --json '{"bridge_url":"ws://127.0.0.1:4311","default_profile":"assist_readonly","default_model":"gpt-5.4"}'
```

Use `config-entry` when you want the Home Assistant config-entry lifecycle
directly, rather than stitching together REST and websocket calls through
`raw`.

#### Pyscript

```bash
hass-cli pyscript list
hass-cli pyscript reload
hass-cli pyscript stubs
hass-cli pyscript call my_service --arguments entity_id=light.kitchen
hass-cli pyscript call pyscript.my_service --json '{"room":"kitchen"}'
```

#### Logs

```bash
hass-cli logs
hass-cli logs pyscript
hass-cli logs telegram_bot
hass-cli logs codex_app_server
hass-cli logs telegram-bot --case-sensitive
```

`logs` reads Home Assistant's error log and can filter by integration or logger
token while keeping full multi-line records such as tracebacks together. It is
best-effort filtering over the existing error log, not a dedicated per-
integration log API.

#### History

```bash
hass-cli history get --since 30m light.kitchen_light
hass-cli history summary --since 7d sensor.bedroom_temperature
hass-cli history average --since 7d sensor.bedroom_temperature
```

Use `history summary` or `history average` for recorder questions like
"average temperature over the last 7 days" instead of assembling raw
`/api/history/period/...?...` URLs by hand. The summary commands compute a
time-weighted average from recorder history and report coverage so gaps and
`unknown`/`unavailable` periods are visible.

### Registry Commands

- `area`: create, list, rename, and delete areas
- `device`: list devices, rename them, and assign them to areas
- `entity`: list entities, rename them, and assign them to areas

These commands use Home Assistant registry APIs and are marked experimental.

## Output and Filtering

The default table output is useful for interactive work, but most commands also
support:

- `-o json`
- `-o yaml`
- `-o ndjson`
- `--no-headers`
- `--table-format`
- `--sort-by`
- `--columns`

Example:

```bash
hass-cli --output yaml state get light.guestroom
hass-cli --columns ENTITY=entity_id,NAME=attributes.friendly_name,STATE=state state list
hass-cli --sort-by last_changed state history --since 50m light.kitchen_light
```

## Shell Completion

Enable completion in your current shell session:

```bash
source <(_HASS_CLI_COMPLETE=bash_source hass-cli)   # bash
source <(_HASS_CLI_COMPLETE=zsh_source hass-cli)    # zsh
eval "$(_HASS_CLI_COMPLETE=fish_source hass-cli)"   # fish
```

## Development

Set up the repository with `uv`:

```bash
uv sync
```

Run the most common checks:

```bash
uv run python -m pytest
uv run python -m mypy homeassistant_cli tests
uv run pre-commit run --all-files
```

Use the local checkout while developing:

```bash
uv run hass-cli --help
uv run hass-cli automation --help
```

## Notes

- Home Assistant configuration and API surfaces evolve quickly. If you are
  working with a new or niche endpoint, `raw` remains the escape hatch.
- For scripted use, prefer `--output json` or `--output ndjson`.
- Do not store tokens in shell history or commit them to this repository.
