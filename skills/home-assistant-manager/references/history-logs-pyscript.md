# History, Logs, Pyscript, And Feedback

Use this reference for recorder history questions, log inspection, pyscript
operations, and explicit Codex feedback capture.

## Recorder History

```bash
hass-cli history get --since 30m light.kitchen_light
hass-cli history summary --since 7d sensor.bedroom_temperature
hass-cli history average --since 7d sensor.bedroom_temperature
```

Prefer `history summary` or `history average` for questions like "what was the
average bedroom temperature over the last 7 days?" These commands avoid brittle
manual `/api/history/period/...?...` URL construction and handle `unknown` or
`unavailable` states when computing the time-weighted result.

Avoid hand-built raw history URLs with query strings unless the higher-level
`history` commands cannot express the request. If raw history is necessary, pass
the full path as one quoted argument so the shell does not reinterpret `?` or
`&`.

## Logs

```bash
hass-cli logs
hass-cli logs pyscript
hass-cli logs telegram_bot
hass-cli logs integration_domain
```

`logs` is record-aware rather than line-based, so matching exceptions keep their
full traceback blocks. It filters the existing error log snapshot; it is not a
streaming dedicated per-integration log API.

## Pyscript

```bash
hass-cli pyscript list
hass-cli pyscript reload
hass-cli pyscript stubs
hass-cli pyscript call my_service --json '{"room":"kitchen"}'
hass-cli pyscript call my_service --arguments key=value,other=value
```

Use `pyscript list` when you need currently exposed custom services and their
fields. It reads the live service registry, so it reflects the running Home
Assistant instance.

## Codex Feedback

Use feedback commands only when explicitly asked to capture problems or
improvement notes about a `hass-cli`-driven turn.

```bash
hass-cli feedback submit "The agent edited the wrong automation" \
  --session-key conversation:test \
  --turn-id turn-123 \
  --profile ha_operator \
  --suggestion "Inspect the exact entity_id before editing." \
  --suggestion "Show the planned diff before writing YAML."

hass-cli feedback retrieve
hass-cli feedback retrieve --all
hass-cli feedback mark-done <feedback_id>
```

`feedback submit` provisions a dedicated Home Assistant `Local To-do` list
named `Codex Feedback` on first use, then stores each feedback entry there.
