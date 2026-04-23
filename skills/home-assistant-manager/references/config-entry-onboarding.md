# Config Entry Onboarding

Use this reference for Home Assistant integration setup, config-entry flow
inspection, and config-entry creation.

## Workflow

1. Confirm the integration is loaded on disk.
2. Check whether a config entry already exists.
3. Discover available flow handlers.
4. Start the flow over REST.
5. Submit flow steps over REST using the returned `flow_id`.

Use websocket for read-only inspection:

```bash
hass-cli -o json raw ws manifest/get --json '{"integration":"integration_domain"}'
hass-cli -o json raw ws config_entries/get
```

Use REST for flow discovery and creation:

```bash
hass-cli -o json raw get /api/config/config_entries/flow_handlers
hass-cli -o json raw post /api/config/config_entries/flow --json '{"handler":"integration_domain","show_advanced_options":false}'
hass-cli -o json raw post /api/config/config_entries/flow/<flow_id> --json '{"field":"value"}'
```

## Gotchas

- Do not assume Home Assistant exposes config-entry flow creation on websocket.
- If `raw ws config_entries/flow/init` or a similar command returns
  `unknown_command`, switch to the REST endpoints.
- Use `/api/config/config_entries/flow_handlers` to confirm the integration is
  registered before starting the flow.
- Use `manifest/get` plus `config_entries/get` to distinguish "integration
  loaded on disk" from "config entry already created".
