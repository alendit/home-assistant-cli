# Home Assistant CLI

[![PyPI version](https://img.shields.io/pypi/v/homeassistant-cli.svg)](https://pypi.org/project/homeassistant-cli/)
[![License](https://img.shields.io/pypi/l/homeassistant-cli.svg)](LICENSE.md)

`hass-cli` is a command-line client for Home Assistant. It can inspect runtime
state, call services, work with registry objects such as devices and areas, and
manage stored configuration for automations and scripts.

It works against local and remote Home Assistant instances and supports JSON,
YAML, tabular output, and shell completion.

## Installation

`homeassistant-cli` supports Python 3.11 and newer.

Install the latest published release with `uv`:

```bash
uv tool install homeassistant-cli
```

Install the current development branch directly from GitHub:

```bash
uv tool install git+https://github.com/home-assistant-ecosystem/home-assistant-cli@dev
```

You can also install it into an existing Python environment:

```bash
python -m pip install homeassistant-cli
```

Community packages are also available in several ecosystems, including Fedora,
Homebrew, and Nixpkgs. Those packages may lag behind the latest release.

## Setup

Create a long-lived access token in your Home Assistant profile, then point
`hass-cli` at your instance with either flags or environment variables.

```bash
export HASS_SERVER="https://homeassistant.local:8123"
export HASS_TOKEN="<long-lived-access-token>"
```

You can also use:

- `HASS_PASSWORD` for legacy API password setups
- `--cert` for a client certificate
- `--insecure` for self-signed TLS during local testing

If your instance is reachable through discovery, `--server auto` is the default.

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
```

Call services:

```bash
hass-cli service list light
hass-cli service call light.turn_on --arguments entity_id=light.kitchen,brightness=180
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

## Current Command Surface

### Core Runtime Commands

- `info`: basic server details
- `config`: configuration details, loaded components, release, whitelist dirs
- `state`: list, get, edit, delete, toggle, turn on/off, and read history
- `service`: list services and call a service
- `event`: interact with the event bus
- `template`: render templates locally or on the server
- `raw`: direct REST and websocket access for advanced workflows

### Typed Home Assistant Commands

These commands give you a more specific interface for common Home Assistant
objects instead of making you stitch everything together through `state`,
`service`, and `raw`.

#### Automations

```bash
hass-cli automation list
hass-cli automation find "lava|motion"
hass-cli automation show automation.kitchen_lights
hass-cli automation trigger automation.kitchen_lights
hass-cli automation disable automation.kitchen_lights
hass-cli automation update automation.kitchen_lights --json '{"alias":"Kitchen Lights"}'
```

`automation show` and `automation update` work with stored automation
configuration and can resolve references from an entity ID, storage ID, or
friendly name.

#### Scripts

```bash
hass-cli script list
hass-cli script find bedtime
hass-cli script show script.goodnight
hass-cli script run script.goodnight --arguments room=bedroom
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

Set up the repository:

```bash
./script/setup
```

Or with `uv`:

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
