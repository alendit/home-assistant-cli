---
name: home-assistant-manager
description: Use when working on Home Assistant configuration, deployment, automation verification, dashboard changes, or remote Home Assistant operations with hass-cli. Prefer direct hass-cli usage for uv tool installs, fall back to repo-local uv usage only when explicitly working from a checkout, and cover approval-safe execution, reload vs restart decisions, and practical verification workflows.
---

# Home Assistant Manager

Use this skill when changing Home Assistant config, testing automations, or
operating a remote Home Assistant instance with `hass-cli`.

## Command Selection

Default to plain `hass-cli`:

```bash
hass-cli state list
hass-cli state get sensor.entity_name
hass-cli service call automation.reload
```

If the user installed `hass-cli` with `uv tool install`, do not prepend
`uv run`. The installed script is already on `PATH`.

Only use the repo-local form when you are explicitly working from this
repository checkout and intentionally want the checkout version instead of the
installed tool:

```bash
uv run hass-cli state list
uv run hass-cli state get sensor.entity_name
uv run hass-cli service call automation.reload
```

## Approval-Safe Command Execution

Some agent approval systems do not auto-approve commands that contain shell
variables such as `$HASS_SERVER` or `$HA_SSH_TARGET`.

When operating in those environments:

1. Do not run `printenv HASS_TOKEN` and do not echo the token back to the user.
2. Let `hass-cli` or the wrapper script read `HASS_TOKEN` from the environment.
3. If you need to confirm the token exists, only report presence:
   `if printenv HASS_TOKEN >/dev/null; then echo HASS_TOKEN_SET; else echo HASS_TOKEN_UNSET; fi`
4. Inline non-secret values such as the resolved server or SSH target only when
   approval rules require literal arguments.
5. Prefer approving a narrow `["hass-cli"]` prefix instead of broad shell
   access.
6. Only if you are intentionally using the repo checkout, prefer a persisted
   rule for the narrow prefix `["uv", "run", "hass-cli"]` instead of broader
   `uv` access.

Example:

```bash
printenv HASS_SERVER

# Then execute with the server literal inlined, but let hass-cli read HASS_TOKEN:
hass-cli --server http://homeassistant.local:8123 state list
```

Same rule for SSH:

```bash
printenv HA_SSH_TARGET

# Then inline the resolved target:
ssh root@homeassistant.local "ha core check"
```

## Prerequisites

Before starting, verify:

1. Home Assistant is reachable over REST with a long-lived token.
2. SSH access exists for host-level `ha` commands when needed.
3. `HASS_SERVER` and `HASS_TOKEN` are exported, or the script you call sets them.
4. You have either an installed `hass-cli` or an explicit reason to use this
   repo's `uv` environment.

## Core Commands

`hass-cli` examples:

```bash
hass-cli state list
hass-cli state get sensor.entity_name
hass-cli automation list
hass-cli automation show automation.name
hass-cli automation export automation.name
hass-cli automation patch automation.name --json '{"mode":"restart"}'
hass-cli script list
hass-cli script export script.name
hass-cli script patch script.name --json '{"mode":"queued"}'
hass-cli scene list
hass-cli pyscript list
hass-cli pyscript reload
hass-cli pyscript stubs
hass-cli pyscript call my_service --json '{"room":"kitchen"}'
hass-cli helper list
hass-cli service list automation
hass-cli service call automation.trigger --arguments entity_id=automation.name
hass-cli config full
hass-cli info
```

Live automation inspection:

```bash
hass-cli -o json state list automation
hass-cli -o json entity list | rg automation
hass-cli state get automation.name
```

Raw API inspection:

```bash
# `raw get config` is normalized to `/api/config`
hass-cli -o json raw get config
hass-cli -o json raw get /api/config
hass-cli -o json raw ws config/device_registry/list
```

Avoid `raw get /config` unless you intentionally want a non-API frontend route.

Pyscript workflows:

```bash
# Discover available pyscript services from the live HA registry:
hass-cli pyscript list

# Reload changed pyscript files and regenerate IDE stubs:
hass-cli pyscript reload
hass-cli pyscript stubs

# Call a custom pyscript service with either shorthand args or JSON:
hass-cli pyscript call linkedgo_sync_temp_offset \
  --arguments reference_sensor=sensor.reference,target_sensor=sensor.target
hass-cli pyscript call pyscript.virtual_heating_control \
  --json '{"climate_entity":"climate.living_room","switch_entity":"input_boolean.heating_call"}'
```

Use `pyscript list` when you need the currently exposed custom services and
their fields; it reads the live service registry, so it reflects what the
running Home Assistant instance exposes right now.

## Config Entry Onboarding

For integration setup, do not assume Home Assistant exposes config-entry flow
creation on the websocket API. On this host, inspection worked over websocket,
but flow creation only worked over REST.

Use websocket for read-only inspection:

```bash
hass-cli -o json raw ws manifest/get --json '{"integration":"codex_app_server"}'
hass-cli -o json raw ws config_entries/get
```

Use REST for flow discovery and creation:

```bash
hass-cli -o json raw get /api/config/config_entries/flow_handlers
hass-cli -o json raw post /api/config/config_entries/flow --json '{"handler":"codex_app_server","show_advanced_options":false}'
hass-cli -o json raw post /api/config/config_entries/flow/<flow_id> --json '{"bridge_url":"ws://127.0.0.1:4311","default_profile":"assist_readonly","default_model":"gpt-5.4"}'
```

Practical rule:

- if `raw ws config_entries/flow/init` or similar returns `unknown_command`,
  switch to the REST endpoints above instead of guessing more websocket method
  names
- use `/api/config/config_entries/flow_handlers` to confirm the integration is
  registered before starting the flow
- use `manifest/get` plus `config_entries/get` to distinguish "integration
  loaded on disk" from "config entry already created"

Config-backed edit workflow:

```bash
# Inspect the exact stored payload shape accepted by update:
hass-cli -o json automation export automation.name
hass-cli -o json script export script.name

# For small edits, prefer an inline merge patch over stdin:
hass-cli automation patch automation.name --json '{"description":"Updated","mode":"restart"}'
hass-cli script patch script.name --json '{"mode":"queued"}'
```

Do not use `automation show` or `script show` as the template for `update`.
Those commands include runtime fields for operator context, while `export`
returns the update-safe stored payload.

Host-level Home Assistant CLI over SSH:

```bash
ssh root@homeassistant.local "ha core check"
ssh root@homeassistant.local "ha core restart"
ssh root@homeassistant.local "ha core logs | tail -50"
```

Replace `root@homeassistant.local` with the actual SSH target when it differs.

## Reload vs Restart

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

If unsure, check with `ha core check` first, then choose the least disruptive
option that will apply the change.

## Automation Verification

After deploying automation changes:

1. Validate configuration.
2. Reload automations if restart is not required.
3. Manually trigger the automation.
4. Inspect logs.
5. Verify the intended effect in entity state or user-visible behavior.

Suggested sequence:

```bash
ssh root@homeassistant.local "ha core check"
hass-cli service call automation.reload
hass-cli service call automation.trigger --arguments entity_id=automation.name
ssh root@homeassistant.local "ha core logs | grep -i 'automation' | tail -20"
```

For entity-state verification:

```bash
hass-cli state get switch.device_name
hass-cli state get sensor.new_sensor
```

## Deployment Patterns

Use `git` for final changes and `scp` for rapid iteration.

Git-based finalization:

```bash
git add file.yaml
git commit -m "Describe change"
git push
ssh root@homeassistant.local "cd /config && git pull"
```

Rapid iteration:

```bash
scp automations.yaml root@homeassistant.local:/config/
hass-cli service call automation.reload
```

Commit only after the tested state is stable.

## Dashboard Work

For Lovelace storage dashboards:

- changes in `.storage/` usually need deploy plus browser refresh
- registering a brand-new dashboard also requires updating
  `.storage/lovelace_dashboards`
- dashboard registration changes usually require a Home Assistant restart

Validate dashboard JSON before deployment:

```bash
python3 -m json.tool .storage/lovelace.my_dashboard > /dev/null
```

For rapid iteration:

```bash
scp .storage/lovelace.my_dashboard root@homeassistant.local:/config/.storage/
```

## Log Triage

Useful checks:

```bash
ssh root@homeassistant.local "ha core logs | grep -i error | tail -20"
ssh root@homeassistant.local "ha core logs | grep -i 'automation_name' | tail -20"
```

Look for:

- `Initialized trigger`
- `Running automation actions`
- `Error executing script`
- `Invalid data for call_service`
- template type errors

## Best Practices

1. Use plain `hass-cli` by default. Only use `uv run hass-cli` when you are
   explicitly operating from this repo checkout.
2. Never print the token value; let tools read `HASS_TOKEN` directly.
3. Inline non-secret values when approval rules reject `$VAR`.
4. Prefer approving `["hass-cli"]`. Only use `["uv", "run", "hass-cli"]` when
   you are explicitly running from the repo checkout.
5. Start live automation discovery with `state list automation` and `entity list`
   before reaching for raw config endpoints.
6. Prefer typed commands like `automation show`, `script show`, `scene show`,
   and `helper list` before dropping to `raw`.
7. For config-backed edits, prefer `automation export` or `script export` to
   inspect the stored payload, and `automation patch` or `script patch` for
   small inline changes.
8. Avoid heredocs, herestrings, and temp files with `hass-cli`; approval rules
   usually will not auto-match them. Prefer inline `--json` literals.
9. For raw REST calls, prefer `raw get config` or `raw get /api/config`.
10. Run `ha core check` before disruptive operations.
11. Prefer reload over restart when possible.
12. Manually trigger automations after deployment.
13. Check logs after every meaningful change.
14. Verify the resulting state instead of assuming success.
