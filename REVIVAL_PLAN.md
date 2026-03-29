# Home Assistant CLI Revival Plan

Date: 2026-03-29

## Status

Completed in this branch:

- Migrated project workflows and packaging to `uv`
- Restored `hass-cli info` on top of `/api/config`
- Removed stale `/api/discovery_info` assumptions from tests and completions
- Modernized websocket handling for Python 3.14 compatibility
- Increased websocket message size handling for large entity registries
- Replaced `distutils.version.StrictVersion` in the `ha` plugin
- Full local test suite currently passes under `uv`

## Summary

`hass-cli` looks revivable without a rewrite. The current Home Assistant API
still supports most of the CLI surface, but the client has stale assumptions,
stale packaging, and stale release management.

The main problem is not that Home Assistant removed everything. The main
problem is that the published package is old, key compatibility fixes are
unreleased, and a few commands still depend on deprecated or removed behavior.

## What Is Broken

1. `info` is hard-broken.
   - `homeassistant_cli/remote.py` still calls `/api/discovery_info`.
   - Current Home Assistant no longer exposes that endpoint.
   - Open issue: `#441`.

2. The websocket transport is stale.
   - `homeassistant_cli/remote.py` still uses `asyncio.get_event_loop()`.
   - This breaks on Python 3.14.
   - It also does not follow the documented websocket handshake cleanly.
   - Open issue: `#433`.

3. Large entity registries can break websocket-based commands.
   - `entity list` failures reported in `#429` are likely caused by websocket
     message size limits, not by removed Home Assistant functionality.
   - Open PR `#443` raises `aiohttp` `max_msg_size` and likely fixes this.

4. The `ha` plugin has runtime and packaging drift.
   - It still imports `distutils.version.StrictVersion`.
   - It double-calls `restapi()` in helper functions.
   - Users report missing `setuptools` / `distutils` fallout in `#432`.

5. The repo is internally inconsistent.
   - Tests still refer to removed `info` behavior.
   - README still documents `hass-cli info`.
   - Packaging is split between legacy `setup.py` flow and partial Poetry
     migration.

6. Release management is stale.
   - PyPI still shows `0.9.6` from 2022-12-25.
   - The local `dev` branch is much newer and already contains unreleased work.
   - Open issue: `#425`.

## Core Conclusion

This is mostly a stale-client and stale-release problem, not a dead API
problem. Existing functionality can likely be brought back with focused repair
work.

## Recommended Scope

Target:

- Home Assistant current stable release
- Home Assistant `core` `dev`
- Python 3.11, 3.12, 3.13, 3.14
- Existing command set only

Do not combine revival with new feature requests like labels, floors,
categories, or batch rename improvements. Those should wait until the current
surface is stable again.

## Action Plan

### Phase 1: Make Existing Functionality Work Again

1. Replace or restore `info`.
   - Reintroduce `hass-cli info` as a wrapper over `/api/config` and `/api/`,
     or remove it everywhere.
   - Do not leave docs, tests, and examples referencing removed behavior.

2. Rework websocket transport in `homeassistant_cli/remote.py`.
   - Replace `asyncio.get_event_loop()` with `asyncio.run()` or
     `asyncio.Runner`.
   - Implement the documented Home Assistant websocket auth sequence.
   - Improve error handling so websocket failures do not degrade into
     `NoneType` crashes.
   - Increase websocket `max_msg_size`.

3. Merge or recreate the low-risk repair PRs.
   - PR `#443`: websocket message size increase.
   - PR `#437`: salvage useful parts only:
     - `asyncio.run()`
     - `packaging.version.Version`
     - duplicate `restapi()` removal
     - defensive websocket result handling
   - PR `#438`: salvage only the packaging fixes that are correct for this repo.

4. Fix the `ha` plugin for modern Python.
   - Replace `distutils.version.StrictVersion`.
   - Ensure plugin import works without implicit `distutils` availability.
   - Keep one request per action helper.

### Phase 2: Restore Confidence in the Repo

5. Repair tests to match reality.
   - Remove remaining `info` / `/api/discovery_info` assumptions.
   - Add regression tests for:
     - websocket auth flow
     - Python 3.14 websocket operation
     - large websocket responses
     - `ha` plugin import and basic behavior

6. Add smoke coverage against a real Home Assistant instance.
   - At minimum:
     - `config full`
     - `state list`
     - `service list`
     - `area list`
     - `device list`
     - `entity list`

7. Update README and command examples.
   - Remove stale `info` examples if the command stays removed.
   - If `info` returns, document the new implementation and output.
   - Verify setup instructions still match current Home Assistant token flow.

### Phase 3: Ship and Re-establish Maintenance

8. Clean up packaging and CI.
   - Pick one supported build path and make it authoritative.
   - Modernize GitHub Actions.
   - Test on Python 3.11-3.14.

9. Cut a release quickly after compatibility fixes land.
   - A small release would likely resolve most “abandoned/broken” complaints.

10. Resolve ownership.
   - If current maintainers are inactive, revival requires either:
     - a maintained fork, or
     - repo transfer / new maintainers, plus
     - PyPI publish access

Without publish rights and an active maintainer path, technical fixes alone
will not revive the project.

## Estimated Effort

- Minimal revival: a few focused days
- Sustainable revival with CI, tests, docs, and release flow: 1 to 2 weeks

## Evidence Reviewed

- Upstream repo issues:
  - `#441` broken `info`
  - `#433` Python 3.14 websocket failure
  - `#429` `entity list` websocket failure
  - `#432` `ha` plugin packaging/import issue
  - `#425` need for a newer release
  - `#442` project appears abandoned

- Upstream repo PRs:
  - `#443` websocket `max_msg_size` fix
  - `#437` modern Python and websocket handling fixes
  - `#438` packaging fixes

- Local code hotspots:
  - `homeassistant_cli/remote.py`
  - `homeassistant_cli/plugins/ha.py`
  - `homeassistant_cli/autocompletion.py`
  - `tests/test_raw.py`
  - `tests/test_plugins.py`
  - `README.rst`

## Note

During this session the local environment did not have `pytest` installed, so
the test suite was not run here.
