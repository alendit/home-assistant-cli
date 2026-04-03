---
name: home-assistant-manager
description: Use when working on Home Assistant configuration, deployment, automation verification, dashboard changes, or remote Home Assistant operations from this repo. Covers repo-local hass-cli usage via uv, approval-safe command execution with inlined env var values, reload vs restart decisions, and practical verification workflows.
---

# Home Assistant Manager

Use this skill when changing Home Assistant config, testing automations, or
operating a remote Home Assistant instance from this repository.

## Repo-Local Workflow

This repository contains the `hass-cli` implementation. Prefer running it from
the checkout:

```bash
uv run hass-cli state list
uv run hass-cli state get sensor.entity_name
uv run hass-cli service call automation.reload
```

Only prefer a globally installed `hass-cli` if you explicitly need to test the
published tool instead of the current checkout.

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
5. If `uv run` itself needs approval, prefer a persisted rule for the narrow
   prefix `["uv", "run", "hass-cli"]` instead of broader `uv` access.

Example:

```bash
printenv HASS_SERVER

# Then execute with the server literal inlined, but let hass-cli read HASS_TOKEN:
uv run hass-cli --server http://homeassistant.local:8123 state list
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
4. You are using this repo's `uv` environment.

## Core Commands

Repo-local `hass-cli`:

```bash
uv run hass-cli state list
uv run hass-cli state get sensor.entity_name
uv run hass-cli energy show
uv run hass-cli energy device list
uv run hass-cli dashboard show dashboard-electricity
uv run hass-cli automation list
uv run hass-cli automation show automation.name
uv run hass-cli automation export automation.name
uv run hass-cli automation patch automation.name --json '{"mode":"restart"}'
uv run hass-cli script list
uv run hass-cli script export script.name
uv run hass-cli script patch script.name --json '{"mode":"queued"}'
uv run hass-cli scene list
uv run hass-cli pyscript list
uv run hass-cli pyscript reload
uv run hass-cli pyscript stubs
uv run hass-cli pyscript call my_service --json '{"room":"kitchen"}'
uv run hass-cli helper list
uv run hass-cli service list automation
uv run hass-cli service call automation.trigger --arguments entity_id=automation.name
uv run hass-cli config full
uv run hass-cli info
```

Energy workflows:

```bash
# Inspect current Energy dashboard wiring:
uv run hass-cli energy show
uv run hass-cli energy validate
uv run hass-cli energy device list
uv run hass-cli energy grid list

# Add or update an Individual device:
uv run hass-cli energy device add sensor.plug_quooker_power_consumption \
  --rate sensor.0xa4c1385254160acc_power \
  --name "Plug Quooker"

# Remove a mistaken grid source:
uv run hass-cli energy grid clear

# Replace the grid source with a real whole-home meter:
uv run hass-cli energy grid set --energy-from sensor.grid_energy_total
```

Dashboard workflows:

```bash
# Inspect a storage dashboard:
uv run hass-cli dashboard show dashboard-electricity

# Save a full dashboard payload from stdin or a file:
cat dashboard.json | uv run hass-cli dashboard save dashboard-electricity --json -
uv run hass-cli dashboard save --json-file dashboard.json
```

Helper discovery:

```bash
# This now includes integration and utility_meter helpers:
uv run hass-cli helper list
uv run hass-cli helper list --type integration
uv run hass-cli helper list --type utility_meter
```

Live automation inspection:

```bash
uv run hass-cli -o json state list automation
uv run hass-cli -o json entity list | rg automation
uv run hass-cli state get automation.name
```

Raw API inspection:

```bash
# `raw get config` is normalized to `/api/config`
uv run hass-cli -o json raw get config
uv run hass-cli -o json raw get /api/config
uv run hass-cli -o json raw ws config/device_registry/list
```

Avoid `raw get /config` unless you intentionally want a non-API frontend route.

Pyscript workflows:

```bash
# Discover available pyscript services from the live HA registry:
uv run hass-cli pyscript list

# Reload changed pyscript files and regenerate IDE stubs:
uv run hass-cli pyscript reload
uv run hass-cli pyscript stubs

# Call a custom pyscript service with either shorthand args or JSON:
uv run hass-cli pyscript call linkedgo_sync_temp_offset \
  --arguments reference_sensor=sensor.reference,target_sensor=sensor.target
uv run hass-cli pyscript call pyscript.virtual_heating_control \
  --json '{"climate_entity":"climate.living_room","switch_entity":"input_boolean.heating_call"}'
```

Use `pyscript list` when you need the currently exposed custom services and
their fields; it reads the live service registry, so it reflects what the
running Home Assistant instance exposes right now.

Config-backed edit workflow:

```bash
# Inspect the exact stored payload shape accepted by update:
uv run hass-cli -o json automation export automation.name
uv run hass-cli -o json script export script.name

# For small edits, prefer an inline merge patch over stdin:
uv run hass-cli automation patch automation.name --json '{"description":"Updated","mode":"restart"}'
uv run hass-cli script patch script.name --json '{"mode":"queued"}'
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

- `uv run hass-cli service call automation.reload`
- `uv run hass-cli service call script.reload`
- `uv run hass-cli service call scene.reload`
- `uv run hass-cli service call template.reload`
- `uv run hass-cli service call group.reload`
- `uv run hass-cli service call frontend.reload_themes`

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
uv run hass-cli service call automation.reload
uv run hass-cli service call automation.trigger --arguments entity_id=automation.name
ssh root@homeassistant.local "ha core logs | grep -i 'automation' | tail -20"
```

For entity-state verification:

```bash
uv run hass-cli state get switch.device_name
uv run hass-cli state get sensor.new_sensor
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
uv run hass-cli service call automation.reload
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

1. Use `uv run hass-cli` from this repo by default.
2. Never print the token value; let tools read `HASS_TOKEN` directly.
3. Inline non-secret values when approval rules reject `$VAR`.
4. Prefer approving `["uv", "run", "hass-cli"]` over broader `uv` prefixes.
5. Start live automation discovery with `state list automation` and `entity list`
   before reaching for raw config endpoints.
6. Prefer typed commands like `automation show`, `script show`, `scene show`,
   and `helper list` before dropping to `raw`.
7. For config-backed edits, prefer `automation export` or `script export` to
   inspect the stored payload, and `automation patch` or `script patch` for
   small inline changes.
8. Avoid heredocs, herestrings, and temp files with `uv run hass-cli`; approval
   rules usually will not auto-match them. Prefer inline `--json` literals.
9. For raw REST calls, prefer `raw get config` or `raw get /api/config`.
10. Run `ha core check` before disruptive operations.
11. Prefer reload over restart when possible.
12. Manually trigger automations after deployment.
13. Check logs after every meaningful change.
14. Verify the resulting state instead of assuming success.
