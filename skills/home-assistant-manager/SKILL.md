---
name: home-assistant-manager
description: |
  Use when the user asks to operate, inspect, troubleshoot, or change Home Assistant with hass-cli: entity state, service calls, automations, scripts, scenes, helpers, Lovelace dashboards, logs, recorder history, pyscript, config entries, HASS_SERVER, HASS_TOKEN, or remote HA access. Trigger even if they say "HA", "automation", "dashboard", "logs", "history", "entity", or "service call" without naming hass-cli.
---

# Home Assistant Manager

Use this skill for Home Assistant operations with `hass-cli`: live inspection,
configuration-backed edits, automation verification, dashboard changes, logs,
history, pyscript, and remote maintenance.

## Default Workflow

1. Identify whether the request is read-only, a config edit, a service call, or
   host maintenance.
2. Prefer `hass-cli` typed commands before raw API calls.
3. Inspect the live state or exported stored payload before changing anything.
4. For mutating or disruptive work, state the intended action, validate it, then
   execute the smallest reload/restart that applies the change.
5. Verify the result from Home Assistant state, logs, command output, or
   user-visible behavior.

## Command Selection

Default to the installed command:

```bash
hass-cli state list
hass-cli state get sensor.entity_name
hass-cli service call automation.reload
```

Only use the repo-local form when you are explicitly working from this
repository checkout and intentionally want the checkout version:

```bash
uv run hass-cli state list
uv run hass-cli state get sensor.entity_name
uv run hass-cli service call automation.reload
```

If `hass-cli` was installed with `uv tool install`, do not prepend `uv run`.
The installed script is already on `PATH`.

## Secret And Approval Safety

- Never print `HASS_TOKEN`, `HASS_PASSWORD`, or other secret values.
- Let `hass-cli` read `HASS_TOKEN` from the environment.
- If you must confirm a token exists, report only presence or absence.
- Inline non-secret values such as a resolved server URL only when approval
  rules require literal arguments.
- Prefer narrow command approvals such as `hass-cli` or `uv run hass-cli`.
- Avoid heredocs, herestrings, and temporary JSON files for `hass-cli`; prefer
  inline `--json` literals or checked-in files that already exist.

Presence check:

```bash
if printenv HASS_TOKEN >/dev/null; then echo HASS_TOKEN_SET; else echo HASS_TOKEN_UNSET; fi
```

## Prerequisites

Verify the relevant prerequisites before acting:

- Home Assistant is reachable over REST with a long-lived token.
- `HASS_SERVER` and `HASS_TOKEN` are exported, or explicit CLI options are
  provided.
- SSH access exists for host-level `ha` commands when those are needed.
- The installed `hass-cli` is appropriate, or this repo checkout is the intended
  command source.

## Core Commands

```bash
hass-cli info
hass-cli config full
hass-cli state list
hass-cli state get sensor.entity_name
hass-cli automation list
hass-cli automation show automation.name
hass-cli automation export automation.name
hass-cli automation patch automation.name --json '{"mode":"restart"}'
hass-cli script list
hass-cli script export script.name
hass-cli script patch script.name --json '{"mode":"queued"}'
hass-cli script run script.name --json '{"room":"kitchen","brightness":180}'
hass-cli scene list
hass-cli helper list
hass-cli service list automation
hass-cli service call automation.trigger --arguments entity_id=automation.name
hass-cli service call light.turn_on --json '{"entity_id":"light.kitchen","brightness":180}'
hass-cli raw get config
```

Use `--arguments` only for flat key/value service data. For nested payloads,
lists, quoted strings, or values containing commas or equals signs, prefer
`--json` or `--json-file`.

For services that return a payload, request the response and allow enough time:

```bash
hass-cli --timeout 120 service call --return-response domain.service --json '{"key":"value"}'
```

## Read-Only Inspection

Start with typed commands:

```bash
hass-cli -o json state list automation
hass-cli -o json entity list
hass-cli state get automation.name
hass-cli service list light
```

Use raw API only when typed commands cannot express the request:

```bash
hass-cli -o json raw get config
hass-cli -o json raw get /api/config
hass-cli -o json raw ws config/device_registry/list
```

Avoid `raw get /config` unless you intentionally want a non-API frontend route.

## Config-Backed Edits

Use exported stored payloads as the source for edits:

```bash
hass-cli -o json automation export automation.name
hass-cli -o json script export script.name
hass-cli automation patch automation.name --json '{"description":"Updated","mode":"restart"}'
hass-cli script patch script.name --json '{"mode":"queued"}'
```

Do not use `automation show` or `script show` as update templates. They include
runtime fields for operator context, while `export` returns the stored payload.

## Reload, Restart, And Verification

Prefer reload over restart whenever possible.

Usually reloadable:

- `hass-cli service call automation.reload`
- `hass-cli service call script.reload`
- `hass-cli service call scene.reload`
- `hass-cli service call template.reload`
- `hass-cli service call group.reload`
- `hass-cli service call frontend.reload_themes`

Usually restart required:

- new integrations in `configuration.yaml`
- core configuration changes
- platform-level sensors that are not reloadable
- dashboard registration changes in `.storage/lovelace_dashboards`

Automation verification loop:

```bash
ssh root@homeassistant.local "ha core check"
hass-cli service call automation.reload
hass-cli service call automation.trigger --arguments entity_id=automation.name
hass-cli state get switch.device_name
```

Replace `root@homeassistant.local` with the actual SSH target. Use host-level
`ha core check`, `ha core restart`, or `ha core logs` only when host access is
actually required.

## References

Load only the file needed for the current request:

- [Config entry onboarding](references/config-entry-onboarding.md): integration
  manifests, config entries, and REST-vs-websocket flow creation.
- [History, logs, and pyscript](references/history-logs-pyscript.md): recorder
  history, time-weighted summaries, logs, pyscript, and feedback commands.
- [Dashboard and deployment](references/dashboard-deployment.md): Lovelace
  storage dashboards, deploy patterns, log triage, and mutation guardrails.

## Gotchas

- `raw get config` is normalized to `/api/config`; `/config` is a frontend route.
- Prefer `history summary` or `history average` over hand-built raw history URLs.
- `hass-cli logs <filter>` filters existing error-log records; it is not a
  streaming per-integration log API.
- If `raw ws config_entries/flow/init` returns `unknown_command`, use the REST
  config-entry flow endpoints instead of guessing websocket method names.
- Commit Home Assistant config only after the tested state is stable.
