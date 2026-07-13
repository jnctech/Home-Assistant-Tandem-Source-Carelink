# Change Register — ha-tandem-pump

Significant changes to this repository, listed in reverse chronological order.

---

## CR-260713-daily-accumulator-zero — Daily carb/bolus totals report 0 (not "unknown") when none today
**Date:** 2026-07-13
**Branch:** `feature/iss-260523-v2-domain-rename`
**Status:** Implemented + remote tests 381 pass (not yet deployed live)

### What changed
| Area | Change |
|------|--------|
| `coordinator.py` `_compute_insulin_summary` | `daily_carbs`, `daily_bolus_total`, `daily_bolus_count` now report **0** over an empty today-set (on a successful fetch) instead of `UNAVAILABLE`/None. A discrete daily accumulator over zero logged events is a genuine 0 ("none yet today"), not missing data — so the tile reads 0 from midnight instead of "unknown" until the first event. |
| (unchanged, deliberately) | `daily_basal_total` + `total_daily_insulin` stay `UNAVAILABLE` when empty: basal is **continuous**, so an empty event window is a data gap and 0 would misrepresent "no insulin delivered" (null-not-guess). |
| `tests/test_expanded_data.py` | `test_no_bolus_events_unavailable`→`_reports_zero` and `test_no_carbs_unavailable`→`_reports_zero`, now asserting `== 0`. |

### Why
`daily_carbs` read "unknown" earlier in the day (before any carb was logged), which reads as a fault on a
dashboard. This is the discrete-accumulator half of the "unknown sensors" review; the event-gated raw
sensors (bolus BG, PLGS, suspend reason) are left as genuine absence.

---

## CR-260713-bolus-calc-surfacing — Surface bolus correction/food that the source has but sensors hid
**Date:** 2026-07-13
**Branch:** `feature/iss-260523-v2-domain-rename`
**Status:** Implemented + remote tests 381 pass + deployed to live HA & validated

### What changed
| Area | Change |
|------|--------|
| `coordinator.py` (bolus-calc join) | Removed the **BG-gate**: the 3-way wizard join accepted a record as "complete" only if `bg is not None` (`:1225`), so a **carb-only bolus** (carbs entered, no fingerstick BG — the norm when bolusing off CGM) was dropped entirely, hiding its carbs+food. Records now anchor on the msg3 completion timestamp; `last_bolus_bg` alone stays unavailable when no BG was entered (genuine absence). |
| `coordinator.py` (correction source) | `last_bolus_correction` now sourced from the latest **completed** bolus delivery (event 280 `correction_mu`), NOT the wizard join. This is the same field that already feeds the LTS "correction" statistics, so correction surfaces on **every** bolus (quick or wizard), not just wizard-with-BG. `0.00` = a bolus with no correction. |
| `coordinator.py` (PII in logs) | The INFO "Parse done" line logged a **raw glucose value** (`CGM=<NNN> mg/dL`) every poll. Now logs `CGM=present/none` + freshness age only — medical reading no longer written to the HA log. |
| `tests/test_expanded_data.py` | Added `_make_bolus_delivery` (event 280) helper; updated 3 tests (correction now from 280; msg3-only surfaces food; stale bg=0 comment); added 5 tests (carb-only-no-BG surfaces carbs/food, correction-from-280-without-wizard, latest-delivery-wins, incomplete-delivery-ignored). |

### Why (root cause)
User observed the Tandem Source / t:connect website shows bolus correction/carbs that HA read as "unknown".
Investigation (live event-count log + LTS import counts: correction=84, carb=16, bolus=96 in-window)
proved the data **is** in the API — it already feeds long-term statistics — but the live "last_*" sensors
were sourced only from the BG-gated wizard join. This is a surfacing/derivation gap, not missing data.

### Verification
| Gate | Result |
|------|--------|
| Remote pytest (docker 3.13) | ✅ **381 passed** (+5 new), 140 snapshots unchanged |
| Golden snapshot | ✅ unchanged (fixture's only event-280 is `delivery_status=1`, no wizard events → correctly still "unknown") |
| Live deploy (scp `coordinator.py` + `ha core restart`, backup `.bak-20260713-preboluscalc`) | ✅ `last_bolus_correction`→value, `last_bolus_food_portion`→value, PII log now `CGM=present`, no errors |

### Follow-ups (not in this change)
Food-portion + carbs for **non-wizard** (quick) boluses — needs `food = delivered_total − correction`
(event 280) with an extended/bolex caveat; deferred pending a `bolus_type` enum check (proposal drafted,
awaiting decision). `daily_carbs` left as-is (event 48 works; "unknown" = no standalone carb entry that day).
`last_bolus_bg`, `predicted_glucose`, `suspend_reason`, battery voltage/remaining remain genuine
condition-gating (ENH-260713 for the battery pair).

---

## CR-260713-oauth-redirect-authfix — Fix v2 live auth (OAuth redirect not followed) + config-flow translations
**Date:** 2026-07-13
**Branch:** `feature/iss-260523-v2-domain-rename`
**Status:** Fixed + live-validated on real pump; RC-blocker for v2.0.0

### What changed
| Area | Change |
|------|--------|
| `tandem_api.py` | Authorize GET now passes `follow_redirects=True`. The OAuth authorization code arrives via a 302 to `…/callback?code=…`; the injected Home Assistant client (`get_async_client`) defaults to `follow_redirects=False`, so the code was never captured → `TandemAuthError: No authorization code in redirect URL` → surfaced as `invalid_auth`. Regression introduced by the inject-websession refactor (CR-260710); the old standalone client had `follow_redirects=True`. |
| `translations/en.json` | Replaced 6 `[%key:common::config_flow::…%]` references with literal English strings (`Invalid authentication`, `Failed to connect`, etc.). Core resolves `[%key:]` at build time; a custom component ships them as-is, so HA rendered the raw key `[%key:common::config_flow::error::invalid_auth%]` to the user. `strings.json` left as the reference-form source. |
| `tests/test_tandem_api.py` | Added `test_login_authorize_follows_redirects` — asserts the authorize GET is called with `follow_redirects=True`. The existing login tests pre-set `mock_auth_resp.url` (simulating an already-followed redirect), which is why unit tests were green while live auth failed. |

### How found / validated
Live-validated via `/validate-live-tandem` after manually staging v2.0.0-rc.1 to the running HA
(`domain=tandem`). Root cause read from the in-memory `system_log` (`No authorization code in redirect URL`).
Post-fix: config entry `loaded`, 70 `tandem_*` entities, `binary_sensor.tandem_data_stale` present.
⚠️ Unit tests (`test_tandem_api.py`, `test_tandem_config_flow.py`) need a **remote** run to confirm the new
test passes (local pytest not run per project rule).

---

## CR-260712-untrack-internal-docs — Untrack internal docs leaked to public repo
**Date:** 2026-07-12
**Branch:** `feature/iss-260523-v2-domain-rename` (HEAD `20e7ddc`)
**Status:** Done — pushed to `origin` (public); `gitea` mirror push failed (ISS-260712-gitea-token-expired)

### What changed
| Area | Change |
|------|--------|
| `.gitignore` | Single-file exclusion (`docs/internal/oob-standards-pointer.md`) replaced with the whole `docs/internal/` directory — session handoffs, oob governance pointers, and reverse-eng notes now ignored wholesale. |
| tracking | `git rm -r --cached docs/internal/` — untracked `RESUME-greenfield-refactor-2026-07-10.md`, `hacs-default-submission.md`, `tandem-source-api-binary-events.md` (local copies retained). |

### Exposure assessment (why history was NOT scrubbed)
The 3 files were tracked + public on `origin/develop`+`origin/master` since 2026-03-16 (~4 months).
Full read of all three: **no PII, no credentials, no secret config** — only internal-process references
(oob governance, build paths, SHAs) and reverse-engineered protocol IP; the HACS submission file was
public-by-design. **Decision: stop future tracking, leave history intact.** A scrub would rewrite
develop+master+5 branches+tags v1.5.0/v1.6.0 across two remotes, break draft PR #70 + the RC release,
and still not retract copies already cloned/forked/cached — disproportionate for non-secret content
with nothing to rotate. (Operator-ratified this session.)

---

## CR-260712-v2-rc-release — Publish v2.0.0-rc.1 (Tandem-only rewrite RC)
**Date:** 2026-07-12
**Branch:** `feature/iss-260523-v2-domain-rename` (HEAD `fa606fa`)
**Status:** Released (pre-release) — awaiting live-pump validation

### What changed
| Area | Change |
|------|--------|
| reconcile | Merged `origin/develop` (OpenSSF #64, `GITHUB_TOKEN` permission restriction) into the feature branch → 20 ahead / 0 behind. Tandem rewrite intact; no carelink files resurrected. |
| version | `manifest.json` **1.0.0 → 2.0.0**. Chosen over 1.0.0 so the tag sits above the carelink-era `v1.6.0` and HACS offers it as an upgrade; domain rename + Medtronic/Nightscout removal = SemVer MAJOR. README "fresh start" refs synced v1.0.0 → v2.0.0. |
| release notes | CHANGELOG `[2.0.0-rc.1]` entry (Keep a Changelog + breaking-change callout + compare link); modern highlights-style GitHub release body. |
| release | GitHub **pre-release** `v2.0.0-rc.1` off branch HEAD; `release.yml` built + attached `tandem-2.0.0.zip` + SBOM. Draft PR #70 (feature → develop) opened to run CI. |
| CI (fork) | Re-enabled the `Validate` workflow (was `disabled_inactivity` — GitHub disables fork workflows after ~60d). |

### Why
Deliver an installable RC for live-pump validation (custom-repo + HACS beta) and force release hygiene now. `quality_scale` intentionally stays **bronze** — no Platinum claim until ISS-260712-reconfigure-platinum lands.

### Verification (PR #70 CI, Python 3.13)
| Gate | Result |
|------|--------|
| Python Tests | ✅ 376 passed |
| mypy --strict | ✅ clean |
| hassfest | ✅ pass |
| ruff / bandit / gitleaks | ✅ clean |
| HACS validate | ⚠️ fails only on `brands` (→ ISS-260712-brands-registration); all other sub-checks pass |
| SonarCloud | ⚠️ SONAR_TOKEN 403 expired (→ ISS-004) |
| conflicts | ⚠️ broken 3rd-party action (→ ISS-260712-conflicts-action-broken); PR MERGEABLE |

### Follow-ups
Live test (pump 2026-07-12 PM) → merge PR #70 + promote rc.1 → `v2.0.0`. ISS-004, ISS-260712-brands-registration, ISS-260712-conflicts-action-broken are environmental (operator/upstream).

## CR-260711-strict-typing — Strict typing pass (P4 Platinum) + test-double fidelity refactor
**Date:** 2026-07-11
**Branch:** `feature/iss-260523-v2-domain-rename`
**Status:** In Review

### What changed
| Area | Change |
|------|--------|
| mypy | `[tool.mypy] strict = true`; dropped the `coordinator`/`tandem_api` `ignore_errors` override. All 14 modules pass `mypy --strict` (~150 errors resolved). |
| deps | `types-aiofiles==24.1.0.20240626` added; test image rebuilt. |
| typing (real fixes, not just annotations) | `DeviceInfo` imported from `homeassistant.helpers.device_registry` (not the non-exporting `helpers.entity`); `EntityCategory` from `homeassistant.const`; `config_flow` returns `ConfigFlowResult` + uses `_get_reconfigure_entry()` (removes an unguarded `None.data` path); `TandemEntity(CoordinatorEntity[TandemCoordinator])` generic + per-subclass `sensor_description` narrowing; **`StatisticMetaData` now passes required `mean_type=StatisticMeanType.ARITHMETIC` + `unit_class`** (recorder API added these — was silently missing); `id_token` None-guard in JWT decode; `binascii.Error` (was `base64.binascii`); gather-unpack pre-declarations. |
| exceptions | `TandemApiError`/`TandemAuthError` imported from `.exceptions` (no longer re-exported via `tandem_api`). |
| CI | New `typecheck` job (`mypy --strict`, py3.13); **all CI/dev Python bumped 3.12 → 3.13** (ci.yml, sonarcloud.yml, CONTRIBUTING.md, .devcontainer/Dockerfile) — HA 2026.2 requires 3.13, closes the toolchain skew. |
| tests (operator: "use proper tests") | The 3 statistics test files faked the entire `homeassistant.components.recorder` module via `sys.modules` injection + hand-rolled stand-ins — which is exactly why the `mean_type`/`unit_class` drift was invisible. Replaced with a shared `mock_import` fixture (conftest) that patches only the **real** `async_import_statistics` boundary and keeps HA's real `StatisticMetaData`/`StatisticData`; assertions use subscript access. Net −250 lines of scaffolding. |
| safety | `.gitignore` now blocks `*_diagnostics_*.json` (device-PII dumps — previously unmatched gap). |

### Why
Completes the P4 Platinum `strict-typing` gap (tracked `docs/quality-gates.md`; STANDARDS-tandem §4/§8 had it as TARGET ◐). The test refactor makes recorder-API contract drift fail loudly instead of being masked by a stale stand-in — seed for the estate `test-double-fidelity` amendment oob is adopting into `STANDARD-code-quality §1`.

### Verification (remote docker 3.13)
| Gate | Result |
|------|--------|
| mypy --strict (14 modules) | ✅ clean |
| Tests | ✅ 376 passed + 140 snapshots |
| ruff check / format | ✅ clean |
| bandit / gitleaks | ✅ clean |

---

## CR-260710-greenfield-tandem-v1 — Greenfield Tandem-only V1 (domain carelink → tandem)
**Date:** 2026-07-10
**Branch:** `claude/domain-codebase-refactor-fgc4fv`
**Status:** In Review

### What changed
| Area | Change |
|------|--------|
| domain | `carelink` → `tandem`; `manifest.version` 1.6.0 → 1.0.0; `ConfigFlow VERSION 1`. Clean break, no migration (ADR-007). |
| scope | Removed the Medtronic CareLink path (`api.py`, `CarelinkCoordinator`) and the Nightscout uploader. Tandem t:slim only. |
| structure | House layout: thin `__init__.py` + `coordinator.py` + `entity.py` + `sensor_types.py`/`binary_sensor_types.py` + `diagnostics.py` + `exceptions.py` + `util.py`. Research (decoders, sensor maps, region auth) moved verbatim. |
| safety | Fail-visible staleness — stale decision-input sensors go unavailable; new `binary_sensor.tandem_data_stale` health surface (ADR-008; STANDARD-stable-anchor rule 3). |
| tests | Deleted carelink/nightscout suites; retargeted Tandem suite; added syrupy entity-goldens + invariants (ADR-009). 373 passing, 88% coverage. |
| toolchain | HA 2026.2 / Python 3.13; `pyproject.toml` coverage gate (80%) + mypy config; CI paths `carelink → tandem`. |
| docs/i18n | strings/en.json aligned to the single-step flow (nightscout/carelink fields removed); stale de/fr/nl/ru translations removed; README/info/TROUBLESHOOTING made Tandem-only; `docs/quality-gates.md` added (tier + Platinum gap). |

### Why
HACS default store rejected the `carelink`-domain submission (mismatched domain, Medtronic +
Nightscout baggage). This re-bases the proven Tandem research as a coherent, single-purpose
integration aiming HA Quality Scale Platinum.

### Follow-ups (not in this change)
inject-websession, strict-typing pass (coordinator/tandem_api), `runtime_data` migration,
entity translations — tracked in `docs/quality-gates.md` and the resume note.

---

## CR-260316-iss-012-hacs-compliance — HACS Compliance Fixes (ISS-012)
**Date:** 2026-03-16
**Branch:** `feature/iss-012-hacs-compliance`
**PR:** TBD
**Status:** In Review

### What Changed
| Area | Change |
|------|--------|
| config_flow.py | Added `async_set_unique_id` + `_abort_if_unique_id_configured` for both Tandem and Carelink flows — prevents duplicate config entries (F-1) |
| config_flow.py | Added `async_step_reauth` + `async_step_reauth_confirm` — reauth flow triggered by `ConfigEntryAuthFailed` (F-7) |
| __init__.py | `TandemAuthError` in coordinator now raises `ConfigEntryAuthFailed` instead of `UpdateFailed` — triggers automatic reauth (F-9) |
| __init__.py | Client construction wrapped in try/except → `ConfigEntryNotReady` for both Carelink and Tandem setup paths (F-8) |
| __init__.py | `_migrate_legacy_logindata` called via `await hass.async_add_executor_job()` — no longer blocks event loop (A-6) |
| manifest.json | Requirements pinned: `aiofiles==24.1.0`, `certifi==2024.12.14`, `httpx==0.28.1` (H-4) |
| manifest.json | Added `integration_type: hub` (H-11) and `loggers: ["httpx"]` (H-9) |
| __init__.py | Carelink coordinator: split login from data fetch, `login()=False` raises `ConfigEntryAuthFailed` (AUTH-01) |
| helpers.py | Entity `unique_id` includes `entry_id` — prevents collisions in multi-entry setups (ENT-01) |
| strings.json, translations/en.json | Added `reauth_confirm` step strings and `reauth_successful` abort reason |
| tests/test_config_flow.py | 9 new tests: unique ID (4), reauth flow (5) |
| tests/test_carelink_coordinator.py | Added Carelink login-returns-False test; updated login exception test |
| tests/test_coordinator_error_paths.py | Updated auth error test: `ConfigEntryNotReady` → `ConfigEntryAuthFailed` |

### Why
HACS default repository submission (PR #6316) requires compliance with HA integration best practices. The HACS baseline review (2026-03-16) identified 6 HIGH, 2 MEDIUM, and 2 LOW findings. This CR resolves 5 HIGH, 2 MEDIUM, and 1 LOW — with A-4a deferred as accepted risk (major refactor, clients already lifecycle-managed).

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | TBD (CI) | ⏳ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| Bandit | Clean | ✅ |

---

## CR-016 — OpenSSF Security Baseline (Phase 7)
**Date:** 2026-03-14
**Branch:** `feature/openssf-security-baseline`
**PR:** [#60](https://github.com/jnctech/ha-tandem-pump/pull/60)
**Status:** Merged

### What Changed
| Area | Change |
|------|--------|
| .github/workflows/*.yml | SHA-pinned all GitHub Actions references (9 actions across 7 workflows) |
| .github/dependabot.yml | Added `github-actions` ecosystem (weekly, targets develop) alongside existing `pip` |
| .github/workflows/scorecard.yml | New: OpenSSF Scorecard analysis (weekly + push to master/develop), publishes SARIF to GitHub Security tab |
| .github/workflows/dependency-review.yml | New: blocks PRs introducing dependencies with moderate+ CVEs or AGPL/GPL-3.0 licenses |
| SECURITY.md | Added Security Measures section documenting all automated controls |

### Why
OpenSSF security baseline is a prerequisite for HACS submission. SHA-pinning prevents supply chain attacks via tag mutation. Dependabot for GitHub Actions keeps pinned SHAs current. Scorecard provides a public supply chain security score. Dependency review prevents introducing vulnerable or incompatibly-licensed dependencies.

### Quality Gate Results (at merge)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | 641 passed | ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| Bandit | Clean | ✅ |
| Actionlint | Clean | ✅ |
| SonarCloud | Passed | ✅ |
| Dependency review | Passed | ✅ |

---

## CR-015 — Estimated Remaining Insulin (Phase 6)
**Date:** 2026-03-13
**Branch:** `feature/estimated-insulin-remaining-phase6`
**PR:** [#58](https://github.com/jnctech/ha-tandem-pump/pull/58)
**Status:** Merged & deployed

### What Changed
| Area | Change |
|------|--------|
| const.py | Added `TANDEM_SENSOR_KEY_ESTIMATED_INSULIN_REMAINING` constant and `SensorEntityDescription` (MEASUREMENT, no device_class, "U", precision 1) |
| __init__.py | Added `_compute_estimated_remaining_insulin()` method with cumulative seq-based delivery tracking |
| __init__.py | Added 4 state variables on TandemCoordinator for cross-poll persistence (`_last_cartridge_fill_seq`, `_last_cartridge_fill_volume`, `_cumulative_delivered`, `_last_delivery_seq`) |
| __init__.py | Added call site with `(KeyError, TypeError, IndexError, ValueError, AttributeError)` exception handling and `exc_info=True` |
| tests | Added `TestEstimatedRemainingInsulin` (10 tests) including cumulative tracking, cartridge reset, edge cases |

### Why
Estimated remaining insulin is the most-requested missing sensor — it tracks how much insulin is left in the cartridge by subtracting cumulative deliveries from fill volume. Uses incremental seq-based accumulation to avoid both double-counting (overlapping 14-day API windows) and upward drift (events aging out of window). No new API decoders needed — computed from existing events (33 cartridge fill, 20/21 bolus, 280/279 basal).

### New Sensor
| Sensor | Device Class | Unit | Notes |
|--------|-------------|------|-------|
| Estimated insulin remaining | None | U | Computed; state lost on HA restart, shows UNAVAILABLE until cartridge fill appears |

### Design Decisions
- **Cumulative seq-based tracking** — avoids critical drift bug where events aging out of 14-day window caused remaining to drift UPWARD (dangerous direction for medical device)
- **State on coordinator** — `_cumulative_delivered` persists across polls but lost on HA restart; acceptable because cartridge fill events stay in 14-day window for ~2 weeks
- **Seq filtering** — `_last_delivery_seq` set to `fill_seq` on cartridge reset, ensuring pre-fill deliveries are excluded without timestamp comparison

### Tests
- 10 tests: basic bolus, extended bolus, basal rate×interval, clamped at zero, no fill, zero fill, new fill reset, pre-fill exclusion, empty events, cross-poll cumulative persistence
- Cumulative tracking verified: poll 1 (5.0 U) + poll 2 (3.0 U) = 8.0 U total, remaining 192.0

### Review Gate Results
| Gate | Result |
|------|--------|
| silent-failure-hunter | 10 findings (R-1 to R-9), all addressed — missing seq/field guards, logging, error→warning |
| code-reviewer | 1 finding (R-10): negative basal interval — fixed with max(0.0, ...) clamp |

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | TBD | ⏳ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | N/A (no API changes) | ✅ |
| Bandit | TBD | ⏳ |

---

## CR-014 — Devcontainer Gitleaks Download Fix
**Date:** 2026-03-14
**Branch:** `bugfix/devcontainer-gitleaks-download`
**PR:** [#57](https://github.com/jnctech/ha-tandem-pump/pull/57)
**Status:** Merged

### What Changed
| Area | Change |
|------|--------|
| .devcontainer/Dockerfile | Added `--retry 3 --retry-delay 5` to gitleaks curl download |
| .devcontainer/Dockerfile | Added `-L` to explicitly follow HTTP redirects |
| .devcontainer/Dockerfile | Removed `--proto-redir -all,https` (redundant — GitHub redirect chain is HTTPS only) |
| .devcontainer/Dockerfile | Added SHA256 checksum verification (`sha256sum -c`) — resolves SonarCloud Security Hotspot |

### Why
Devcontainer build was failing intermittently with `gzip: stdin: unexpected end of file` — the gitleaks tarball download was completing partially due to transient network interruption. The `--proto-redir` flag was also potentially suppressing the redirect follow-through in some curl versions. Added retry logic, explicit `-L`, and SHA256 integrity verification to make the download resilient and satisfy SonarCloud's security analysis.

### Quality Gate Results
| Metric | Value | Gate |
|--------|-------|------|
| Python tests | N/A (no Python changes) | — |
| Ruff format | N/A | — |
| Bandit | N/A | — |
| API drift | N/A | — |

---

## CR-013 — PLGS & Daily Status Sensors (Phase 5)
**Date:** 2026-03-13
**Branch:** `feature/plgs-daily-status-phase5`
**PR:** [#55](https://github.com/jnctech/ha-tandem-pump/pull/55)
**Status:** Merged & deployed

### What Changed
| Area | Change |
|------|--------|
| tandem_api.py | Added decoders for event 140 (PLGS Periodic) and event 90 (NewDay) |
| tandem_api.py | Added events 90 and 140 to API event filter string |
| const.py | Added `TANDEM_SENSOR_KEY_PREDICTED_GLUCOSE` constant and `SensorEntityDescription` |
| __init__.py | Added PLGS event categorisation, sorting, and predicted glucose sensor population |
| __init__.py | Added NewDay event collection and logging (sensor population deferred to Phase 6) |

### Why
PLGS (Predictive Low Glucose Suspend) events contain the pump's predicted glucose value — useful for dashboards showing what Control-IQ "sees" ahead of actual CGM readings. NewDay events capture the commanded basal rate at midnight, decoded for diagnostics and future Phase 6 use.

### New Sensor
| Sensor | Device Class | Unit | Notes |
|--------|-------------|------|-------|
| Predicted glucose | BLOOD_GLUCOSE | mg/dL | From PLGS algorithm PGV; 0 = UNAVAILABLE (No Prediction) |

### Tests
- 8 decoder tests (PLGS states, unknown fallback, NewDay rate/features)
- 7 coordinator tests (latest-wins, zero PGV, no events, combined events)
- 641 total passing

### Review Gate Results
| Gate | Result |
|------|--------|
| Logic Review 1 (Opus) | No issues found |
| silent-failure-hunter | No new findings |
| code-reviewer | No new findings |

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | 641 passed | ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |
| Bandit | Clean | ✅ |

---

## CR-012 — Bolus Calculator Attributes Bugfix
**Date:** 2026-03-13
**Branch:** `bugfix/bolus-calc-attrs-not-sensor`
**PR:** [#53](https://github.com/jnctech/ha-tandem-pump/pull/53)
**Status:** Merged & deployed

### What Changed
| Area | Change |
|------|--------|
| const.py | Removed `TANDEM_SENSOR_KEY_BOLUS_CALC_ATTRS` SensorEntityDescription — dict values are not valid HA sensor states |
| const.py | Changed constant value to `"tandem_last_bolus_bg_attributes"` so bolus calc details surface as `extra_state_attributes` on `last_bolus_bg` sensor via the existing `_attributes` convention in `sensor.py` |

### Why
Code review (post-merge on PR #52) identified that the `bolus_calculator_attributes` sensor was passing a dict as `native_value`. HA sensors require scalar values. The existing codebase pattern for attribute dicts (e.g., `LAST_BOLUS_ATTRS`, `LAST_MEAL_BOLUS_ATTRS`) stores them as coordinator data keys with `_attributes` suffix but does NOT register them as SensorEntityDescriptions. Applied the same pattern.

---

## CR-011 — Bolus Calculator Sensors (Phase 4)
**Date:** 2026-03-13
**Branch:** `feature/bolus-calculator-phase4`
**PR:** [#52](https://github.com/jnctech/ha-tandem-pump/pull/52)
**Status:** Merged & deployed (bugfix in CR-012)

### What Changed
| Area | Change |
|------|--------|
| tandem_api.py | Added 3 event constants (EVT_BOLUS_REQUESTED_MSG1=64, MSG2=65, MSG3=66) |
| tandem_api.py | Added 3 decoder cases for bolus calculator messages (BG, carbs, IOB, ISF, food/correction split) |
| tandem_api.py | Updated get_pump_events() event_ids to include 64, 65, 66 |
| const.py | Added 5 sensor key constants and 4 SensorEntityDescriptions (5th removed in CR-012) |
| __init__.py | Added 3-way join by BolusID across msg1/msg2/msg3 events |
| __init__.py | Populate 4 primary sensors + attributes dict from latest complete bolus calc record |
| tests | Added TestBolusCalcDecoder (6 tests) + TestBolusCalcCoordinator (8 tests); 627 total passing |

### Sensors Added
| Key | Name | Value |
|-----|------|-------|
| tandem_last_bolus_bg | Last bolus BG | mg/dL at time of bolus request (+ bolus calc details as extra_state_attributes) |
| tandem_last_bolus_carbs_entered | Last bolus carbs entered | grams entered into calculator |
| tandem_last_bolus_correction | Last bolus correction | units (correction portion) |
| tandem_last_bolus_food_portion | Last bolus food portion | units (food portion) |

### Review Gate Results
| Gate | Result |
|------|--------|
| Logic Review 1 (Opus) | No bugs; 2 low-severity notes (B-1, B-2) |
| API Drift Review 2 (Opus) | No drift (binary events not in JSON fixture) |
| Sensor Review 3 (Sonnet) | All correct |
| silent-failure-hunter | No new findings (pre-existing C-4 noted) |
| code-reviewer | 1 critical finding — dict-as-sensor (fixed in CR-012) |

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | 627 passed | ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |
| Bandit | Clean | ✅ |

---

## CR-010 — G7, Libre 2 CGM Support & Sensor Type Detection (Phase 3)
**Date:** 2026-03-13
**Branch:** `feature/cgm-g7-libre2-phase3`
**PR:** #50, #51
**Status:** Merged & deployed

### What Changed
| Area | Change |
|------|--------|
| tandem_api.py | Added 3 event constants (EVT_AA_DAILY_STATUS=313, EVT_CGM_DATA_FSL2=372, EVT_CGM_DATA_G7=399) |
| tandem_api.py | Added 3 decoder cases (G7 same layout as GXB, FSL2 different int16/uint8 layout, AA_DAILY_STATUS for sensor type) |
| tandem_api.py | Updated get_pump_events() event_ids to include 313, 372, 399 |
| const.py | Added CGM sensor type key constant and SensorEntityDescription (diagnostic, icon mdi:chip) |
| __init__.py | Replaced ALL magic event IDs with EVT_* constants (import from tandem_api) |
| __init__.py | Route events 399/372 into cgm_readings alongside 256; parse 313 for sensor type |
| __init__.py | Updated LTS statistics to include G7 and FSL2 CGM events |
| __init__.py | Narrowed exception handling: `except Exception` → `except (KeyError, TypeError, IndexError)`, warning → error |
| __init__.py | Added logging for unknown CGM sensor types |
| tests | Added TestCGMPhase3Decoder (11 tests) + TestCGMPhase3Coordinator (8 tests); 613 total passing |

### Sensors Added
| Key | Name | Value |
|-----|------|-------|
| tandem_cgm_sensor_type | CGM sensor type | G6, G7, Libre 2, None, or Unknown (N) — from AA_DAILY_STATUS event 313 |

### Review Gate Results
| Gate | Result |
|------|--------|
| Logic Review 1 (Opus) | No bugs; 7 low-severity test-coverage suggestions |
| API Drift Review 2 (Opus) | No drift; FSL2 uint8 vs uint16 status noted — can't validate without real capture |
| Sensor Review 3 (Sonnet) | All correct |
| silent-failure-hunter | 6 findings; 4 fixed (magic numbers, exception narrowing, unknown type logging, error severity) |
| code-reviewer | Pending final run |

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | 613 passed | ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |
| Bandit | Clean | ✅ |

---

## CR-009 — Alerts & Alarms Sensors (Phase 2)
**Date:** 2026-03-13
**Branch:** `feature/alerts-alarms-phase2`
**PR:** [#49](https://github.com/jnctech/ha-tandem-pump/pull/49)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA

### What Changed
| Area | Change |
|------|--------|
| tandem_api.py | Added 5 event constants (EVT_ALERT_ACTIVATED=4, EVT_ALARM_ACTIVATED=5, EVT_MALFUNCTION_ACTIVATED=6, EVT_ALERT_CLEARED=26, EVT_ALARM_CLEARED=28) |
| tandem_api.py | Added 3 decoder cases; updated get_pump_events() event_ids to include 4, 5, 6, 26, 28 |
| const.py | Added 3 sensor key constants, TANDEM_ALERT_MAP (~35 entries), TANDEM_ALARM_MAP (~29 entries), 3 SensorEntityDescription entries |
| __init__.py | Added UNAVAILABLE defaults; updated _parse_pump_events() categorisation; added _parse_alert_alarm_events() |
| tests | Added TestAlertAlarmDecoders (7 tests) + TestAlertAlarmCoordinator (13 tests); 596 total passing |

### Sensors Added
| Key | Name | Value |
|-----|------|-------|
| tandem_last_alert | Last pump alert | Human-readable alert name (TANDEM_ALERT_MAP) |
| tandem_last_alarm | Last pump alarm | Human-readable alarm name (TANDEM_ALARM_MAP) |
| tandem_active_alerts_count | Active pump alerts | Count of uncleared alerts + alarms |

### Review Gate Results
| Gate | Result |
|------|--------|
| silent-failure-hunter | 5 findings; all addressed (comments, error→warning, state_class fix) |
| code-reviewer | 2 findings; both addressed (state_class=None, malfunction comment) |
| Logic Review 1 (Opus) | 2 test gaps; both addressed (name assert + malfunction-cleared test) |
| Sensor Review 3 (Sonnet) | No errors found |

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Tests | 596 passed | ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |
| Bandit | Clean | ✅ |

---

## CR-008 — Display Precision & Fixture Update
**Date:** 2026-03-13
**Branch:** `fix/sensor-display-precision`
**PR:** [#48](https://github.com/jnctech/ha-tandem-pump/pull/48)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (IOB 2dp, basal 3dp, battery 1dp, percentages 1dp)

### What Changed
| Area | Change |
|------|--------|
| const.py | Added `suggested_display_precision` to 25 Tandem sensors (0 for integers, 1 for %/mmol, 2 for insulin, 3 for basal rates) |
| fixture | Rebuilt `known_good_api_response.json` from real API capture — full metadata structure, pumper_info, 16 event samples |
| fixture | Updated `_drift_check` field lists: added `patientName`, profile sub-fields |
| docs | Resolved findings D-2 (drift check), S-4 (accepted), S-5 (fixed) |

### Finding Reference
- S-5: suggested_display_precision was missing from all sensors — HA showed raw float precision
- S-4: No HA `SensorDeviceClass.BLOOD_GLUCOSE` exists — `device_class=None` is correct
- D-2: `partNumber` and `patientName` now in drift check canonical field list

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 83%+ | ≥80% ✅ |
| Tests | 576 passed | — ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |

---

## CR-007 — Sensor Metadata Audit & Battery Voltage Fix
**Date:** 2026-03-13
**Branch:** `fix/sensor-metadata-audit`
**PR:** [#47](https://github.com/jnctech/ha-tandem-pump/pull/47)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (voltage from ShelfMode, duration formatting, diagnostic categories)

### What Changed
| Area | Change |
|------|--------|
| const.py | Duration sensors: bare "h"/"m" → UnitOfTime.HOURS/MINUTES + SensorDeviceClass.DURATION |
| const.py | Battery sensors (conduit, CGM sensor): added SensorDeviceClass.BATTERY |
| const.py | Device info sensors (6 Carelink): added EntityCategory.DIAGNOSTIC |
| const.py | Active insulin, reservoir, max basal: added missing unit_of_measurement |
| const.py | sgBelowLimit: corrected from PERCENT to MGDL (glucose threshold, not percentage) |
| const.py | Tandem sensors: "U"→UNITS, "mV"→UnitOfElectricPotential.MILLIVOLT, "kg"→UnitOfMass.KILOGRAMS |
| tandem_api.py | Removed unreliable DailyBasal voltage (raw ADC, not millivolts) |
| __init__.py | Coordinator: voltage now exclusively from ShelfMode; expanded PII redaction |
| tests | Updated battery decoder/coordinator tests; expanded PII test coverage |

### Finding Reference
- 8 new review findings (S-6 through S-11, P-1) tracked in review-findings.md
- DailyBasal voltage 25344 confirmed as raw ADC via diagnostics capture
- ShelfMode voltage 3722 mV confirmed as accurate

### Quality Gate Results (at branch)
| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 83%+ | ≥80% ✅ |
| Tests | 576 passed | — ✅ |
| Ruff format | Clean | ✅ |
| Ruff lint | Clean | ✅ |
| API drift | None | ✅ |

### Post-Deploy Actions
- [ ] scp updated files to HA
- [ ] `ha core restart`
- [ ] Verify battery voltage shows realistic mV (from ShelfMode) or UNAVAILABLE
- [ ] Verify duration sensors show proper HA duration formatting

---

## CR-006 — Sensor Audit & Diagnostics Service (ISS-011 Support)
**Date:** 2026-03-13
**Branch:** `fix/sensor-audit-diagnostics`
**PR:** [#46](https://github.com/jnctech/ha-tandem-pump/pull/46)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (4 battery entities + diagnostics service)

### What Changed
| Area | Change |
|------|--------|
| __init__.py | Added `capture_diagnostics` service handler — dumps full API response to `/config/carelink_diagnostics_*.json` for field discovery |
| __init__.py | Widened event fetch window from 1 day to 14 days — ensures battery/daily events are captured even with infrequent uploads |
| const.py | Fixed glucose delta sensor: changed unit from `None` to `mg/dL` |
| tandem_api.py | Minor formatting cleanup |
| services.yaml | Added `capture_diagnostics` service definition |
| tests | 8 new tests for `capture_diagnostics` service handler (file write, error handling, service registration) |

### Finding Reference
- Glucose delta unit fix addresses sensor metadata gap found during baseline review
- Diagnostics service enables API schema discovery for future ISS-011 phases
- Event window widening ensures battery sensors (daily cadence) reliably populate

### Quality Gate Results (at merge)
| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 83%+ | ≥80% ✅ |
| Tests | 576 passed | — ✅ |
| Bugs/Vulns/Smells | Grade A | Grade A ✅ |

### Post-Deploy Actions
- [ ] Deploy with CR-005 (same scp + restart)
- [ ] Verify `capture_diagnostics` service appears in Developer Tools → Actions
- [ ] Run service, retrieve diagnostics JSON for fixture update

---

## CR-005 — Battery Monitoring Sensors (ISS-011 Phase 1)
**Date:** 2026-03-12
**Branch:** `feat/phase1-battery-monitoring`
**PR:** [#45](https://github.com/jnctech/ha-tandem-pump/pull/45)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (battery %, voltage, remaining, charging status)

### What Changed
| Area | Change |
|------|--------|
| tandem_api.py | Added event constants EVT_USB_CONNECTED (36), EVT_USB_DISCONNECTED (37), EVT_SHELF_MODE (53), EVT_DAILY_BASAL (81); added 4 binary decoders; added event IDs to API request |
| const.py | Added 4 sensor keys (battery %, voltage mV, remaining mAh, charging status) + SensorEntityDescription entries |
| __init__.py | Added battery sensor categorisation with DailyBasal/ShelfMode priority logic, USB charging status detection |
| tests | 20 new tests: 11 decoder tests (TestBatteryEventDecoders) + 9 coordinator tests (TestBatterySensorPopulation) |

### Finding Reference
- ISS-011 Phase 1 — battery data available in Tandem Source API via event IDs not previously requested
- Battery % formula from tconnectsync: `min(100, max(0, round((256 * (MSB - 14) + LSB) / (3 * 256) * 100, 1)))`

### Quality Gate Results (at merge)
| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 83%+ | ≥80% ✅ |
| Tests | 568 passed | — ✅ |
| Bugs/Vulns/Smells | Grade A | Grade A ✅ |

### Post-Deploy Actions
- [ ] scp updated files to HA (`tandem_api.py`, `const.py`, `__init__.py`)
- [ ] `ha core restart`
- [ ] Verify 4 new battery entities appear (battery %, voltage, remaining mAh, charging status)
- [ ] Confirm battery % matches pump display (within daily update cadence)

---

## CR-004 — Fix Sensor state_class Metadata (S-1, S-3)
**Date:** 2026-03-12
**Branch:** `fix/sensor-state-class`
**PR:** [#40](https://github.com/jnctech/ha-tandem-pump/pull/40)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (62 entities, no errors)

### What Changed
| Area | Change |
|------|--------|
| const.py | Removed `state_class=MEASUREMENT` from 3 discrete event sensors (last bolus, last meal bolus, last cartridge fill) — these are one-time events, not continuous measurements |
| const.py | Removed `state_class=MEASUREMENT` from 5 daily total sensors — daily-reset accumulators produce meaningless HA long-term statistics with MEASUREMENT |

### Finding Reference
- S-1 (Medium): Discrete event sensors with MEASUREMENT produce meaningless mean/min/max statistics
- S-3 (Medium): Daily totals with MEASUREMENT instead of None confuse HA statistics

### Impact
Existing HA long-term statistics for affected sensors will stop accumulating. No data loss — historical values remain but new entries won't be added. Users who relied on statistics graphs for these sensors will see them stop updating.

---

## CR-003 — Fix Suspend Reason Lookup Bug (L-1)
**Date:** 2026-03-12
**Branch:** `bugfix/l1-suspend-reason`
**PR:** [#39](https://github.com/jnctech/ha-tandem-pump/pull/39)
**Status:** Merged to `develop`
**Deployed:** 2026-03-13 — verified on HA (no errors)

### What Changed
| Area | Change |
|------|--------|
| Coordinator | Removed redundant `SUSPEND_REASON_MAP` lookup — `suspend_reason` is already decoded to a human-readable string by `tandem_api.py` |
| const.py | Removed unused `SUSPEND_REASON_MAP` constant |
| Tests | Updated `_suspend_event` helper to pass string values matching real API output |

### Finding Reference
Baseline review L-1 (Medium): `SUSPEND_REASON_MAP` has int keys but `suspend_reason` field is a string from the API decoder. Lookup always returned `None`, producing `"Unknown (User)"` instead of `"User"`.

---

## CR-002 — Engineering Controls Gap Closure
**Date:** 2026-03-12
**Branch:** `feature/test-gitea-ci`
**PR:** [#37](https://github.com/jnctech/ha-tandem-pump/pull/37)
**Status:** Merged to `develop`

### What Changed
Full implementation of engineering controls to meet quality gate and security requirements.

| Area | Change |
|------|--------|
| Secret scanning | Gitleaks CI job + pre-commit hook + `.gitleaks.toml` |
| CI hardening | SonarCloud blocking gate, `pip-audit`, Anchore SBOM |
| Dockerfile linting | `hadolint` CI job added |
| Workflow linting | `actionlint` CI job added |
| Dev container | `.devcontainer/`, `docker-compose.dev.yml` |
| Test container | `Dockerfile.test`, `docker-compose.test.yml` |
| Inner-loop CI | `.gitea/workflows/ci.yml` (runner: 192.168.30.10) |
| API drift detection | `scripts/check_api_drift.py`, `tests/test_api_drift.py` |
| Sensor doc generation | `scripts/generate_sensor_docs.py` |
| Known-good fixture | `tests/fixtures/known_good_api_response.json` |
| Dependencies | `tzdata` added to `requirements.txt` |
| Docs | `SECURITY.md`, `CONTRIBUTING.md` rewrite, `README.md`, `info.md`, `docs/reviews/README.md` |
| Dependabot | `.github/dependabot.yml` |

### Quality Gate Results (at merge)
| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 83% | ≥80% ✅ |
| Tests | 549 passed | — ✅ |
| Bugs/Vulns/Smells | Grade A | Grade A ✅ |
| Gitea CI time | ~54s | <3min ✅ |
| SonarCloud | PASSED | Blocking ✅ |

### Post-Deploy Actions
- ✅ `SONAR_TOKEN` added to GitHub Actions secrets — 2026-03-12
- ✅ GitHub branch protection required checks wired on `master` and `develop` — 2026-03-12
- ✅ `develop` pulled on docker host via `git pull github develop` — 2026-03-12

---

## CR-001 — Initial Fork Setup
**Date:** 2026-01-xx
**Status:** Merged to `master`

### What Changed
- Forked from upstream (noiwid/HAFamilyLink pattern)
- Initial sensor definitions for Tandem t:slim via Medtronic Carelink
- Example dashboard
- Basic GitHub Actions CI

---
