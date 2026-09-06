# ADR-009: Entity-golden tests (syrupy snapshots + invariants)

**Date:** 2026-07-10
**Status:** Accepted
**Relates:** ported from `jnctech/homeassistant-mikrotik_router` ADR-014.

## Context

Entity-surface behaviour (which entities exist, their state, attributes, and registry entry)
was only indirectly tested via coordinator logic tests. The platform wiring
(`async_setup_entry` → entities) had little coverage, and hand-asserted entity tests are
brittle — every new attribute means editing many asserts.

## Decision

Adopt a layered taxonomy with **entity-golden (snapshot) tests** as the entity-surface layer:

- **L0 — logic unit tests:** parsing / compute / staleness, against the coordinator directly.
- **L1 — entity goldens** (this ADR): set the integration up through the **real** path
  (`MockConfigEntry` + `async_setup`, the Source client mocked at the boundary), then snapshot
  every entity's state + attributes + registry entry with syrupy `snapshot_platform`
  (`tests/snapshots/*.ambr`).
- **L2 — flow tests:** config / reauth / reconfigure.

**Rules:**

1. **Golden PAIRED with load-bearing invariant asserts.** A snapshot alone can be silently
   re-blessed wrong; the invariant encodes the contract the bug would violate (glucose in
   physiological range, mg/dL↔mmol/L exact, the health surface off when fresh). Per
   `STANDARD-code-quality-2026-07-04` §1.
2. **Determinism is mandatory.** A fixed `entry_id` (so unique_ids don't churn) and a frozen
   clock just after the fixture's CGM reading (so decision-inputs read fresh). `snapshot_platform`
   asserts one platform per call, so each golden patches `PLATFORMS` to a single platform.
3. **First bless reviewed by hand,** never a blind `--snapshot-update`.

## Alternatives Considered

- **Hand-asserted entity tests.** Brittle and verbose. Rejected — snapshots collapse that to one
  reviewed `.ambr`.
- **Coordinator-data (`self.data`) snapshots.** Unreviewable diffs during refactors; snapshot the
  *entity output*, not the internal dict. Rejected.

## Consequences

- New dev dependency `syrupy` (in `requirements.txt`); `.ambr` files are reviewed artifacts under
  `tests/snapshots/`.
- Goldens exercise the platform funnel through a real `hass`, lifting coverage there.
- `--snapshot-update` is never a reflex — a golden diff is a signal to read, not rubber-stamp.
