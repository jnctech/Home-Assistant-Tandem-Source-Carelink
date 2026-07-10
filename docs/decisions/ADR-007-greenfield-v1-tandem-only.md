# ADR-007: Greenfield V1 — `tandem` domain, Tandem-only, house layout

**Date:** 2026-07-10
**Status:** Accepted

## Context

The integration began as a fork of `yo-han/Home-Assistant-Carelink` (Medtronic CareLink) and
grew Tandem t:slim X2 support bolted alongside it, under the `carelink` domain, with a
Nightscout uploader. HACS's default store **rejected** the submission: the `carelink` domain
does not match the integration's purpose, and it carried two subsystems it shouldn't. The
Tandem code was sound ("dodgy but all researched") but housed in a 2,972-line `__init__.py`
mixing two devices.

## Decision

Ship a **greenfield V1** under the `tandem` domain:

- **Tandem t:slim only.** Remove the Medtronic CareLink path (`api.py`, `CarelinkCoordinator`,
  the carelink config-flow step and constants) and the Nightscout uploader (`nightscout_uploader.py`).
- **Clean break, no migration.** `manifest.version` reset to `1.0.0`, `ConfigFlow VERSION = 1`,
  **no `async_migrate_entry`**. Existing `carelink`-domain users re-add fresh (see README
  "Upgrading"). HA cannot reassign a config entry's domain from a custom component anyway;
  greenfield avoids a fragile cross-domain shim.
- **House layout** (mirrors `jnctech/homeassistant-mikrotik_router`): thin `__init__.py` +
  `coordinator.py` + `entity.py` + declarative `sensor_types.py` / `binary_sensor_types.py` +
  `diagnostics.py` + `exceptions.py` + `util.py`.
- **Research preserved.** The reverse-engineered binary event decoders, sensor mappings, and
  OIDC/PKCE region auth move **verbatim** into `tandem_api.py` / `coordinator.py` — under
  cite-or-null they are cited evidence, not re-guessed.

## Alternatives Considered

- **Keep `carelink` domain + dual-platform.** The status quo HACS rejected; keeps dead Medtronic
  code and a mismatched name. Rejected.
- **Rename in place with a migration path.** Cross-domain entry migration is unsupported for a
  custom component; would need a compatibility shim (fragile) for little benefit given a small
  pre-1.0 user base. Rejected — clean break instead.

## Consequences

- Entity ids become `sensor.tandem_*`; long-term statistic ids are `sensor.tandem_*` by
  construction, fixing the prior double-prefix mismatch (supersedes the `sensor.carelink_*`
  premise in ADR-001).
- Existing users must re-add the integration (documented). No data auto-migrates.
- The dropped Medtronic code path is gone from the tree; docs retain fork attribution.
- Enables the Platinum aim (ADR-008/009, `docs/quality-gates.md`) on a single, coherent surface.
