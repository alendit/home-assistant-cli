# Dashboard And Deployment

Use this reference for Lovelace storage dashboards, Home Assistant config
deployment, and log triage after changes.

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

## Log Triage

```bash
hass-cli logs
hass-cli logs automation
ssh root@homeassistant.local "ha core logs | grep -i error | tail -20"
ssh root@homeassistant.local "ha core logs | grep -i 'automation_name' | tail -20"
```

Look for:

- `Initialized trigger`
- `Running automation actions`
- `Error executing script`
- `Invalid data for call_service`
- template type errors

## Mutation Guardrails

- Inspect the current state before editing or calling services.
- Prefer reloads over restarts.
- Run `ha core check` before disruptive operations when host access is
  available.
- Manually trigger automations after deployment.
- Verify entity state, logs, or UI behavior after every meaningful change.
