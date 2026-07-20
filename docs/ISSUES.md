# Issues & Planned Work — ha-tandem-pump

Tracks repo-specific issues, features, and planned work.
For quick cross-project tasks, see `~/Code/TODO.md`.

---

## In-flight (read first at session start)

**Last session (2026-07-17) — estate mailbox coordination (no product code changed).** Cleared the tandem oob
inbox and replied what was owed (commits on `~/oob`, unpushed — operator serializes the shared-branch push):
(a) **step-5b STANDARDS-tandem confirmation → oob** — operator-directed: recorded the **heavyweight governance
model as the INTENDED TARGET**, lean = current OPERATING state only (do NOT let oob consolidate "lean = canonical");
(b) **v2-live status ping → homeassistant-config** (post-add verify clear); (c) **PII-gitignore correction →
config** (their "urgent" `*_diagnostics_*.json`-absent claim is stale — present at `.gitignore:185`); (d) filled
the oob-advisory pointer-content gaps in `docs/internal/oob-standards-pointer.md` (C2 classification + ratify chain
+ never-self-ratify + C0 gate) → **oob CONFIRMED canon-faithful, item #3 closed**. New ID filed:
**ISS-260717-adr-number-collision** (ADR-007/008/009 clash across branches — confirmed real). gitea-token maps to
existing **ISS-260712-gitea-token-expired** (token is DEAD/rejected — cleanup, not a live leak). **Residual operator
DECISION (low urgency):** whether the already-public pre-`20e7ddc` git history (estate-internal RESUME file, no
secrets/PII) needs a scrub. **Resume priority is UNCHANGED — the product queue below.**

**"Unknown sensors" review → bolus-calc surfacing fixes, deployed live (2026-07-13).** Operator asked why
several sensors read "unknown". Investigation proved most were genuine event-gating, but the bolus-calc
family was a **surfacing gap** (data present — already feeds LTS — but hidden by a BG-gated wizard join).
Shipped on branch `feature/iss-260523-v2-domain-rename` (pushed, HEAD `456eb90`), **deployed to live HA
(manual install, `/config/custom_components/tandem/`) + validated, clean logs:**
- **CR-260713-bolus-calc-surfacing** (`82d0f48`): `last_bolus_correction` ← event 280 `correction_mu`
  (every bolus); removed the BG-gate so carb-only boluses surface carbs/food; dropped a raw-glucose value
  from an INFO log line (PII). Remote **381 pass**.
- **CR-260713-daily-accumulator-zero** (`8c37f4e`): `daily_carbs`/`daily_bolus_total`/`_count` report **0**
  (not "unknown") when none logged today; basal/TDI left unavailable-when-empty (continuous ≠ zero).
- Live cross-check vs pump ground truth (12 g meal bolus): `daily_carbs`=12 ✓ (carb decode validated).

**Next session prompt (resume tomorrow, 2026-07-14+):** operator away on business; pump was offsite.
(1) **ISS-260713-event280-offset-verify** — the load-bearing open item: notes vs code disagree on event-280
`correction_mu` offset; the deployed correction value + option-A food-portion depend on it. Need a t:connect
cross-check of the **correction** portion for a **meal bolus where food ≠ correction** (a correction-only
bolus can't distinguish; carb decode already validated). (2) Decide **ENH-260713-last-bolus-vs-meal-bolus**
(should `last_bolus_*` skip Control-IQ auto-corrections and track the last *meal* bolus?). (3) **ISS-260713-msg3-total-bolus-garbage**
(fix the `total_bolus_size` decode). (4) Optional per operator: **option A food-portion** (once offset
confirmed), interim-revert of the correction source if zero-risk wanted meanwhile. Standing/unchanged:
**promote to final `v2.0.0`** once **SONAR_TOKEN rotated** (ISS-004); then P4 **ISS-260712-reconfigure-platinum**.

**rc.2 live-validation (2026-07-13):** `/validate-live-tandem` re-run — **PASS**, safety invariants intact,
Dexcom cross-check within tolerance. Internal report: `docs/internal/validate-live-tandem-2026-07-13-rc2.md`.
Context: v2 (`domain=tandem`) live == rc.2 + this session's fixes; PR #70 merged to develop; feature branch not deleted.

---

## Current Priorities

1. **Promote to final `v2.0.0`** (In-flight above) — rc.2 live-validated + PR #70 merged; tag off develop when ready. Gate: SONAR_TOKEN rotation (ISS-004).
2. **ISS-260712-reconfigure-platinum** — last P4 item; reconfigure/repair polish → flip quality_scale bronze→platinum
3. **ISS-004** — rotate expired SONAR_TOKEN (SonarCloud 403); **ISS-260712-brands-registration** — home-assistant/brands PR
4. **ISS-012** — HACS review findings (older; verify still relevant post-rewrite)
5. **ISS-005** — tandem_api.py coverage gap

---

## Active

### ISS-260712-reconfigure-platinum — Reconfigure/repair polish → Platinum flip
**Type:** Quality / HA Quality Scale
**Priority:** High (last P4 item)
**Created:** 2026-07-12
**Status:** 🟡 Open
Last remaining P4 Platinum item. Polish the reconfigure + repair flows, then flip
`custom_components/tandem/manifest.json` `quality_scale` **bronze → platinum** and re-run
hassfest / HACS validate. The v2.0.0-rc.1 release intentionally ships at `bronze` — no Platinum
claim until this lands and validates. Tracked long-form in `docs/quality-gates.md` / STANDARDS-tandem §4.

### ISS-260713-orphan-carelink-statistics — Purge leftover old-carelink statistics from HA recorder
**Type:** Ops / live-HA cleanup (not a repo code change)
**Priority:** Low (cosmetic)
**Created:** 2026-07-13
**Status:** 🟡 Open — user-side HA action
After the carelink→tandem migration, HA's recorder still holds statistic_ids under the old
`sensor.<child>_s_bedroom_t_slim_2_*` names (never purged when the old `carelink` integration was
uninstalled). On v2 startup HA logged collisions (`Cannot rename statistic_id … already exists`,
`Cannot migrate history for entity_id …`). Harmless — v2 produces clean `sensor.tandem_*` entities —
but the stale long-term stats linger. Fix: HA → Developer Tools → Statistics → resolve the flagged
"issues" (fix/remove the orphaned ids), or script via the recorder. No code impact.

### ISS-260713-event280-offset-verify — Verify event-280 correction_mu / delivered_total_mu byte offsets
**Type:** Correctness / binary decode (medical field)
**Priority:** High (gates food-portion work; validates a deployed change)
**Created:** 2026-07-13
**Status:** 🟡 Open — BLOCKED on pump availability (offsite); operator to verify vs t:connect
**Source:** CR-260713-bolus-calc-surfacing follow-up; `/validate-live-tandem` offset-sensitivity rule

The reverse-eng notes (`docs/internal/tandem-source-api-binary-events.md:59-65`) and the live decoder
(`tandem_api.py:172-180`) **disagree** on event-280 offsets:

| Field | Notes | Code |
|-------|-------|------|
| `correction_mu` | offset 6 | offset **8** |
| `delivered_total_mu` | offset 8 | offset **12** |

The deployed `last_bolus_correction` fix (CR-260713) reads `correction_mu` at **offset 8**, and the
deferred food-portion derivation (option A: `food = delivered_total − correction`) depends on BOTH
offsets. Cannot be resolved by inspection — the golden fixture is circular (decoded by the same code)
and plausible-looking LTS values are not proof. **Offset-sensitive binary field = silent-decode risk.**

**Progress 2026-07-13 (partial):** operator gave ground truth "last meal bolus 12 g @ 13:38". `daily_carbs`
read **12 exactly → carb decode (event 48) VALIDATED.** But the correction offset is still unresolved: the
most-recent bolus HA saw was a **correction-only** 0.2 U bolus (correction == total), which cannot
distinguish a right vs wrong `correction_mu` offset. **Still need a bolus where food ≠ correction.**

**Verification (operator, when pump on-site):** for a recent **meal bolus with a correction portion**
(food ≠ correction), read the **correction amount** on the t:connect / Tandem Source dashboard and compare
to `sensor.tandem_last_bolus_correction` — noting HA's "last bolus" may be a later Control-IQ correction
([[ENH-260713-last-bolus-vs-meal-bolus]]), so match the *bolus_id*/time, not just "the latest".
- Match → code offset 8 confirmed → proceed with option A (guard extended boluses via event 21).
- Mismatch → fix the decode offset first; the deployed correction value is wrong and must be corrected.
Cross-check aid: for a *wizard* bolus, event 66 `correction_bolus_size` (float) is an independent decode
of the same correction — it should equal event 280 `correction_mu / 1000`.

**Interim risk:** `last_bolus_correction` may currently show a wrong (historical, informational) value
instead of the prior "unknown". Low risk (not a live decision-input). Revert-the-source option available
if zero-risk preferred (keeps the safe BG-gate/carbs/food surfacing, which uses a different decode).

### ISS-260713-msg3-total-bolus-garbage — Bolus-calc `total_bolus_size` decodes to garbage
**Type:** Correctness / binary decode
**Priority:** Medium (attribute-only; signals decode fragility)
**Created:** 2026-07-13
**Status:** 🟡 Open
**Source:** Live cross-check 2026-07-13 — `sensor.tandem_last_bolus_bg` attr `total_bolus` = `7.4e26`.

Event 66 (`BolusRequestedMsg3`) `total_bolus_size` is decoded as `>f` at **offset 10**
(`tandem_api.py:464`) and returns a garbage float (~7.4e26) on live data — misaligned or reading past
a short payload (food@2 + correction@6 fit; total@10 needs ≥14 bytes). `food_bolus_size`@2 and
`correction_bolus_size`@6 decode fine. Surfaces only in the `BOLUS_CALC_ATTRS` dict (not a primary
sensor), so low blast radius, but it is concrete evidence of the binary-decode fragility flagged in
[[ISS-260713-event280-offset-verify]]. Fix: verify the true offset/length of `total_bolus_size` against
a raw capture (and guard NaN/inf so garbage never reaches an attribute).

### ENH-260713-last-bolus-vs-meal-bolus — "Last bolus" sensors track any bolus incl. Control-IQ corrections
**Type:** Enhancement / UX (behaviour design)
**Priority:** Medium
**Created:** 2026-07-13
**Status:** 🟡 Open — needs operator decision
**Source:** Live cross-check 2026-07-13 — pump last *meal* bolus was 12 g @ 13:38, but HA `last_bolus_*`
showed a later ~14:46 **0.2 U correction-only** bolus (likely a Control-IQ auto-correction).

The `last_bolus_bg / carbs_entered / correction / food_portion` sensors reflect the **most recent bolus
of any kind**. Control-IQ fires frequent small carb-less correction boluses, so those will usually *be*
the most recent — meaning `last_bolus_carbs`/`bg` read blank even right after a meal bolus. `daily_carbs`
is unaffected (correctly summed 12 g). **Decision needed:** should the "last bolus" family track the last
**meal/user bolus** (one carrying carbs, or excluding CIQ auto-corrections via `bolus_type`) instead of
the last any-bolus? Small, safe change if so. Depends on distinguishing CIQ-correction vs user bolus in
the event data (bolus_type bitmask — see [[ISS-260713-event280-offset-verify]] for the enum).

### ENH-260713-battery-shelfmode-unknown — Battery voltage/remaining permanently "unknown" on worn pump
**Type:** Enhancement / UX
**Priority:** Low
**Created:** 2026-07-13
**Status:** 🟡 Open
**Source:** `/validate-live-tandem` v2.0.0-rc.2 gate (internal report 2026-07-13)

`sensor.tandem_pump_battery_voltage` (mV) and `sensor.tandem_pump_battery_remaining` (mAh) are
sourced **only** from ShelfMode events (event 53, `coordinator.py:1102-1108`); DailyBasal (event 81)
supplies battery **%** only. A pump in normal daily wear rarely/never enters ShelfMode, so both
sensors read `unknown` indefinitely — not a fault (null-not-guess: no fabricated default), but two
dashboard entities that never populate for the typical user. `battery_level` (%) is unaffected and
reports correctly. Options: (a) leave as-is (accurate null), (b) document in TROUBLESHOOTING,
(c) hide/derive when ShelfMode has never been seen. Behaviour verified correct at rc.2; cosmetic only.

### ISS-260712-brands-registration — Register `tandem` domain in home-assistant/brands
**Type:** Distribution / HACS
**Priority:** Medium (blocks HACS default listing, NOT custom-repo install)
**Created:** 2026-07-12
**Status:** 🟡 Open — needs operator go (upstream PR)
HACS `validate` fails only on the `brands` sub-check: the `tandem` domain is not in the
`home-assistant/brands` repository (renamed from `carelink`, never re-added). Needs an **upstream**
PR to `home-assistant/brands` adding `custom_integrations/tandem/` with `icon.png` + `logo.png`
(brand assets do not yet exist — must be created). Does not block the RC or a custom-repo beta
install (placeholder icon only). Do not open the upstream PR without explicit operator go-ahead.

### ISS-260712-conflicts-action-broken — `conflicts` CI workflow fails to build
**Type:** CI hygiene
**Priority:** Low
**Created:** 2026-07-12
**Status:** 🟡 Open
The `conflicts` check (`mschilde/auto-label-merge-conflicts`) fails on PR #70 — its Docker image
won't build (`yarn: not found`). Not a real merge conflict (PR is MERGEABLE); pure infra noise.
Pin the action to a working ref, replace it with a maintained equivalent, or remove the workflow.

### ISS-260712-gitea-token-expired — Gitea mirror push rejected (dead embedded token)
**Type:** Infra hygiene
**Priority:** Low
**Created:** 2026-07-12
**Status:** 🟡 Open
The `gitea` remote (`gitea.colebungalow.com/jc/ha-tandem-pump`) has an access token embedded in the
`.git/config` URL that is now **rejected** (`Unauthorized`) — expired or revoked. Push of `20e7ddc`
to the mirror failed, so the gitea mirror is ≥1 commit behind `origin`. The dead plaintext token is
harmless (not live) but should be cleaned up. Fix: refresh the token or switch the remote to SSH /
a credential helper (stop storing a plaintext token in the URL), then re-push the branch.

### ISS-260717-adr-number-collision — ADR-007/008/009 defined differently across branches
**Type:** Docs hygiene / merge risk
**Priority:** Medium (hard collision if both branches merge)
**Created:** 2026-07-17
**Status:** 🟡 Open
Verified across branches this session: `feature/iss-260523-v2-domain-rename` defines ADR-007=greenfield-v1-tandem-only,
008=fail-visible-staleness, 009=entity-golden-tests; `feature/iss-012-hacs-compliance` defines the SAME numbers as
007=entity-unique-id-format, 008=cumulative-insulin-tracking, 009=httpx-async-client. Disjoint decisions under
identical IDs → hard collision if both merge. Surfaced via config's 07-17 standards-intake forward (§2). **Proposed
resolution (not executed):** whichever branch merges second renumbers its ADRs to 010/011/012 with redirect stubs.
Confirmed real to oob in `RELAY-from-tandem-to-oob-standards-intake-step5b-confirmation-2026-07-17.md`; flagged as
still warranting the `ledger/recover → main` promote_check G2 hold.

### ISS-260720-carelink-naming-residue — Stale `carelink` naming in user-facing service description
**Type:** Bug / Docs
**Priority:** Low (user-visible, non-functional)
**Created:** 2026-07-20
**Status:** ✅ Resolved 2026-07-20
Two stale `carelink` references survived the domain rewrite:
- `services.yaml:29` — the `capture_diagnostics` description shown in **Developer Tools → Actions**
  told users the snapshot is written to `/config/carelink_diagnostics_<timestamp>.json`. The code
  actually writes `tandem_diagnostics_<timestamp>.json` (`__init__.py:300`, and the docstring at
  `__init__.py:203` was already correct) — so users following the UI text looked for a file that
  never exists. **Real user-facing defect**, not cosmetic.
- `coordinator.py:2081` — section comment `# Helper functions (Carelink)` (cosmetic).
Both corrected. Found while investigating an operator report that the setup screen still mentioned
Medtronic/Nightscout — that specific report was **not** reproducible: `strings.json` and
`translations/en.json` are Tandem-only (config-flow translations were fixed in v2.0.0-rc.2, see
CR-260713-oauth-redirect-authfix). The operator was most likely viewing the old `carelink`-domain
integration still installed in HA. **Unconfirmed — worth a 10-second check at next live session.**

### ISS-012 — HACS Review Findings
**Type:** Quality / HACS Compliance
**Priority:** High
**Created:** 2026-03-16
**Status:** 🟢 Active — PR in progress
**Source:** `docs/reviews/review-hacs-2026-03-16.md`

**HIGH findings resolved:**
- [x] F-1: `async_set_unique_id` + `_abort_if_unique_id_configured` in config flow
- [x] F-9: Auth errors raise `ConfigEntryAuthFailed` (triggers reauth)
- [x] F-8: Pre-coordinator setup failures wrapped in `ConfigEntryNotReady`
- [x] A-6: `_migrate_legacy_logindata` sync I/O wrapped in `async_add_executor_job`
- [x] H-4: Requirements pinned to exact `==` versions

**Deferred (accepted risk):**
- A-4a: Own httpx.AsyncClient — major refactor, clients lifecycle-managed. Not blocking for HACS.

**MEDIUM resolved:**
- [x] H-11: `integration_type: hub` added to manifest
- [x] F-7: Reauth flow (`async_step_reauth` + `async_step_reauth_confirm`) implemented

**LOW resolved:**
- [x] H-9: `loggers` list added for httpx

**Reference:** HACS submission PR: https://github.com/hacs/default/pull/6316

### ISS-010 — Architecture Decision Records & Documentation Gaps
**Type:** Documentation / Engineering Practice
**Priority:** Medium
**Created:** 2026-03-13
**Status:** 🟢 Active — ADRs + templates done, tooling remaining

**Done:**
- ✅ ADR-001 through ADR-006 (PR #41, merged)
- ✅ PR template + issue templates (PR #42, merged)

**Remaining:**
- ADR-007 (test coverage targets) — needs research
- ADR-008 (unit consistency: "U" vs "units") — needs research
- CHANGELOG.md + generator
- Release checklist action
- Pre-push hook
- Commit message validation
- Dependency pinning
- ~~**Devcontainer build fix**~~ — ✅ Fixed in CR-014 (`bugfix/devcontainer-gitleaks-download`): added `--retry 3`, `-L` flag, dropped redundant `--proto-redir`

**Reference:** Plan file `peaceful-sauteeing-star.md`

### ISS-011 — Tandem API Expansion (Battery & Beyond)
**Type:** Feature / Upstream Sync
**Priority:** High
**Created:** 2026-03-13
**Status:** 🟢 Active — Phase 6 deployed & verified, Phase 7 next

Upstream review of yo-han/Home-Assistant-Carelink (17 commits since fork point `ac6f2a3`) found **no new battery/reservoir sensors upstream**. Battery data IS available in the Tandem Source API via event IDs not previously requested.

**Phase 1 (Battery Monitoring) — ✅ Complete:**
- PR #43: Investigation docs (upstream review + 6-phase plan) — merged
- PR #44: Housekeeping (ISSUES.md updates) — merged
- PR #45: Battery monitoring implementation — merged
- PR #46: Sensor audit + diagnostics service — merged
- 4 new sensors: battery %, voltage (mV), remaining (mAh), charging status
- `capture_diagnostics` service for API schema discovery
- Widened event fetch window (1→14 days) for reliable battery data
- Fixed glucose delta unit (None → mg/dL)
- 28 new tests (20 battery + 8 diagnostics), 576 total passing
- ✅ Deployed & verified 2026-03-13. See CR-005, CR-006.
- ⚠️ Battery voltage (18944 mV) may be raw ADC — investigate with diagnostics capture

**Phase 2 (Alerts & Alarms) — ✅ Deployed & verified:**
- PR #49 — merged to develop, deployed 2026-03-13
- 3 new sensors: last_alert, last_alarm, active_alerts_count
- TANDEM_ALERT_MAP (~35 entries) + TANDEM_ALARM_MAP (~29 entries) in const.py
- 20 new tests (7 decoder + 13 coordinator), 596 total passing
- See CR-009

**Phase 3 (G7 & Libre 2 CGM) — ✅ Deployed & verified:**
- PR #50 + PR #51 (SonarCloud S1871 fix) — merged to develop, deployed 2026-03-13
- 1 new sensor: cgm_sensor_type (diagnostic, from AA_DAILY_STATUS event 313)
- G7 (event 399) and Libre 2 (event 372) CGM readings routed into existing cgm_readings pipeline
- Replaced all magic event IDs in coordinator with EVT_* constants
- Extracted `_decode_cgm_gxb_layout` shared decoder to eliminate duplication
- 19 new tests (11 decoder + 8 coordinator), 613 total passing
- See CR-010

**Phase 4 (Bolus Calculator) — ✅ Deployed & verified:**
- PR #52 (implementation) + PR #53 (bugfix: remove dict-as-sensor, use _attributes pattern)
- 4 new sensors: last_bolus_bg, last_bolus_carbs_entered, last_bolus_correction, last_bolus_food_portion
- Bolus calculator details surfaced as extra_state_attributes on last_bolus_bg (not a standalone sensor)
- 3-way join by BolusID across events 64/65/66
- 14 new tests (6 decoder + 8 coordinator), 627 total passing
- Sensors show "unknown" until bolus calculator wizard is used (quick boluses are event 17, not 64/65/66)
- See CR-011, CR-012

**Phase 5 (PLGS & Daily Status) — ✅ Deployed & verified:**
- PR #55 — merged to develop, deployed 2026-03-14
- 1 new sensor: predicted_glucose (from PLGS algorithm PGV, event 140)
- Event 90 (NewDay) decoded for diagnostics logging; sensor deferred to Phase 6
- 15 new tests (8 decoder + 7 coordinator), 641 total passing
- Sensor shows "unknown" until a PLGS event occurs (expected — PLGS only activates on predicted low)
- See CR-013

**Phase 6 (Estimated Remaining Insulin) — ✅ Deployed & verified:**
- PR #58 — merged to develop, deployed 2026-03-14
- 1 new sensor: estimated_insulin_remaining (cumulative seq-based tracking)
- Compute-then-commit pattern prevents state corruption on exceptions
- 11 new tests, 652 total passing
- Sensor shows "unknown" until cartridge fill event appears in 14-day window (expected)
- See CR-015

**All 6 implementation phases complete.** Remaining:
1. ~~Phase 1: Battery Monitoring~~ — ✅ Done
2. ~~Phase 2: Alerts & Alarms~~ — ✅ Done
3. ~~Phase 3: G7 & Libre 2 CGM~~ — ✅ Done
4. ~~Phase 4: Bolus Calculator~~ — ✅ Done
5. ~~Phase 5: PLGS & Daily Status~~ — ✅ Done
6. ~~Phase 6: Estimated Remaining Insulin~~ — ✅ Done

7. ~~Phase 7: OpenSSF Security Baseline~~ — ✅ Done (PR #60, merged 2026-03-14)
   - SHA-pinned 9 actions, dependabot github-actions, scorecard, dependency-review
   - ⏳ Opus compliance review → `docs/reviews/review-openssf-YYYY-MM-DD.md` (next session)

**Investigation items:**
- CGM sensor change tracking (Dexcom G6 10-day cycle) — check if any undecoded event ID corresponds to sensor insertion/removal. Phase 3 CGM events (399, 372, 313) may include this.
- CGM transmitter change tracking (Dexcom G6 3-month cycle) — check if transmitter pairing/unpairing events exist in undecoded event IDs.

**Reference:** `docs/upstream-review-2026-03-12.md`, `docs/plan-tandem-api-expansion.md`

---

## Backlog

### ISS-005 — `tandem_api.py` Coverage at 47% (below 80% file-level)
**Type:** Quality / Testing
**Priority:** Medium
**Created:** 2026-03-12
**Status:** 🟡 Backlog

Overall coverage is 83% (passes gate), but `tandem_api.py` is at 47% line coverage individually. The SonarCloud gate measures project-wide, so this passes — but the API client is the highest-risk file and deserves dedicated test coverage.

**Suggested approach:**
- Audit what isn't covered in `tests/test_tandem_api.py`
- Add tests for error paths, session handling, and retry logic
- Target ≥80% on this file specifically

---

### ISS-006 — Gitea Mirror of GitHub develop/master
**Type:** Infrastructure / Workflow
**Priority:** Low
**Created:** 2026-03-12
**Status:** 🟡 Backlog

Docker host's Gitea remote (`origin`) only has the inner-loop CI workflow. Pushing merged `develop` to Gitea requires removing branch protection (done 2026-03-12) then pushing manually. A proper mirror setup would auto-sync GitHub→Gitea.

**Option A:** Configure Gitea pull-mirror from GitHub (Settings → Repository → Mirror Settings)
**Option B:** Keep as-is (push manually after major merges — low friction for solo workflow)

---

## Completed

### ISS-009 — Fix Sensor state_class Metadata (S-1, S-3)
**Closed:** 2026-03-13 (PR #40)
Removed `state_class=MEASUREMENT` from 8 sensors: 3 discrete events (last bolus, meal bolus, cartridge fill) and 5 daily totals. These produced meaningless HA long-term statistics. See CR-004.

### ISS-008 — Fix Suspend Reason Lookup Bug (L-1)
**Closed:** 2026-03-12 (PR #39)
Removed redundant `SUSPEND_REASON_MAP` lookup — API already returns decoded strings. Standardised unknown-code format. Added defensive try/except. See CR-003.

### ISS-007 — Baseline AI Review
**Closed:** 2026-03-12
Full 3-review baseline pass (Logic, API Drift, Sensor) completed by Opus. 16 findings tracked in `docs/reviews/review-findings.md`. Baseline narrative at `docs/reviews/review-baseline-2026-03-12.md`. PR review template and token-efficiency rules added to CLAUDE.md.

### ISS-003 — GitHub Branch Protection: Required Checks
**Closed:** 2026-03-12
All 9 required checks wired to both `master` and `develop` branch protection rules.

### ISS-004 — SONAR_TOKEN GitHub Actions Secret
**Status:** 🔴 Reopened 2026-07-12 — token expired
`SONAR_TOKEN` was added 2026-03-12 and confirmed working. As of PR #70 (2026-07-12) the SonarCloud
scan fails with **HTTP 403** querying JRE metadata — the token has expired/been revoked. **Action
(operator):** regenerate the token on SonarCloud and update the `SONAR_TOKEN` repo secret. Not a code
issue; does not block the RC or live test.

### ISS-001 — Engineering Controls Gap
**Closed:** 2026-03-12 (PR #37)
Full secret scanning, CI hardening, devcontainer, test container, Gitea inner-loop CI, API drift detection, sensor doc generation. See CR-002 in CHANGE-REGISTER.md.

### ISS-002 — Example Dashboard
**Closed:** 2026-01-xx (PR #34)
Added example Lovelace dashboard with card-mod prerequisites.

---
