# RESUME — greenfield Tandem V1 refactor (2026-07-10)

Session handoff. Everything below is **pushed** to `origin/claude/domain-codebase-refactor-fgc4fv`.
Read this first, then continue at **§ Remaining work**. cite-or-null throughout; `file:line` where it matters.

## Goal (locked decisions)

Pivot `custom_components/carelink/` (a Medtronic fork that grew Tandem support; HACS-default-rejected) into a
**greenfield V1** `tandem`-domain integration: **Tandem t:slim only**, Medtronic + Nightscout removed, restructured to
the maintainer's mikrotik house standards, aiming HA Integration Quality Scale **Platinum**, syrupy goldens.

- **Domain `tandem`** · `manifest.version 1.0.0` · `ConfigFlow VERSION 1` · **no migration** (clean break).
- **Standards template:** `jnctech/homeassistant-mikrotik_router` (cloned at `/workspace/homeassistant-mikrotik_router`).
- **oob estate canon** governs: cloned at `/workspace/oob`. Grounded on `standards/DOCTRINE-oob-operating-concepts.md`.
  Load-bearing: `standards/STANDARD-stable-anchor-reconciliation-2026-07-02.md` (safety), `STANDARD-code-quality-2026-07-04.md`
  (Platinum + spine), `STANDARD-secret-hygiene-2026-06-29.md`, cite-or-null / null-not-guess.
- Full plan: `/root/.claude/plans/encapsulated-dreaming-graham.md` (host-local, not in repo).

## Environment (rebuild if fresh session)

- **venv:** `/tmp/venv` — `python3.13 -m venv`; installs HA **2026.2.3** (last Python-3.13 HA line; 2026.3+ needs 3.14.2,
  which the container lacks), `pytest-homeassistant-custom-component==0.13.316`, `syrupy==5.0.0`, `ruff==0.15.21`,
  `mypy==2.2.0`. Recreate: `python3.13 -m venv /tmp/venv && . /tmp/venv/bin/activate && pip install -r requirements.txt`.
- **Run tests:** `. /tmp/venv/bin/activate && python -m pytest tests/ -q -p no:cacheprovider` (add `--cov` for the 80% gate).
- **Goldens:** `pytest tests/test_sensor_golden.py --snapshot-update` regenerates `.ambr`; **hand-review before trusting**
  (ADR-014). `.ambr` lives at `tests/snapshots/test_sensor_golden.ambr`.
- **No `ssh-keygen`** in the container + the signing key `/home/claude/.ssh/commit_signing_key.pub` is 0 bytes → commits
  are **Unverified** (correct author `Claude <noreply@anthropic.com>`, just unsigned). Not fixable here.

## Done (commits, all pushed, all green: 373 tests, 140 snapshots, 88% cov, ruff clean)

- `14d033f` **P1** greenfield package. `git mv carelink -> tandem`; deleted `api.py`, `nightscout_uploader.py`,
  `CarelinkCoordinator`. New layout: thin `__init__.py` + `coordinator.py` (TandemCoordinator moved verbatim, 1874-line
  slice) + `entity.py` (TandemEntity base) + `sensor_types.py`/`binary_sensor_types.py` + `diagnostics.py` +
  `exceptions.py` + `util.py`. **Safety:** `entity.py::available` — stale decision-inputs go **unavailable**;
  timestamp/settings sensors (`TANDEM_SENSORS_ALWAYS_AVAILABLE`) stay visible. Reversed the old "diagnostic mode" that
  showed stale values as live (and inverted its tests). `unique_id = f"{DOMAIN}_{entry_id}_{key}"` (stable anchor).
- `3bf4a63` **P4a** `TandemDataStaleBinarySensor` (`binary_sensor.tandem_data_stale`, device_class=problem, always
  available) — the stable-anchor rule-3 named health surface.
- `93d593b` **P0** toolchain: `requirements.txt` modern pins; `pyproject.toml` coverage `fail_under=80` + mypy config
  (coordinator/tandem_api `ignore_errors` until their typing pass); CI paths `carelink -> tandem` in
  `.github/workflows/{ci,sonarcloud,release}.yml`, `.gitea/workflows/ci.yml`, `Dockerfile.test`.
- `c0f1cc0` **P3** syrupy goldens: `snapshot` fixture in conftest; `tests/test_sensor_golden.py` — per-platform
  `snapshot_platform` (patch `PLATFORMS` to one platform) + frozen clock + fixed entry_id, **paired with invariants**
  (glucose 120mg/dL/6.66mmol exact, data_stale off when fresh, fail-visible e2e when stale).

## Remaining work

### P4 — Platinum technical rules (`manifest.quality_scale` still `bronze`)
1. **inject-websession** (Platinum): thread `hass` into `TandemSourceClient.__init__` and replace its self-made httpx
   client with `homeassistant.helpers.httpx_client.get_async_client(hass)`. **Watch:** `config_flow.validate_tandem_input`
   and `test_tandem_config_flow.py` construct `TandemSourceClient(email, password, region)` — signature change ripples to
   those + `__init__.async_setup_entry` + `tests/conftest.py`/`test_tandem_stale_data.py` mocks.
2. **strict-typing:** full hints + `mypy --strict`; drop the coordinator/tandem_api `ignore_errors` override
   incrementally (it's honest, not a cheat — do the real typing pass). Wire `.pre-commit-config.yaml` (ruff/mypy/bandit/gitleaks).
3. **runtime_data:** migrate `hass.data[DOMAIN][entry_id]` → `entry.runtime_data` (mikrotik `MikrotikData` pattern).
   Touches `__init__`, both platforms, coordinator ctor, and every test that seeds `hass.data`.
4. **reconfigure/repair** polish; consider `async_get_config_entry_diagnostics` is already present.

### P5 — docs / strings / translations (**gates hassfest/HACS validation** — do before any validate run)
- **`strings.json` + `translations/en.json` are STALE** — still describe the old two-step platform-picker flow +
  nightscout fields. Rewrite for the single `user` step (email/password/region/scan_interval) + `reauth_confirm` +
  `reconfigure`. Non-en (`de/fr/nl/ru`) are carelink-only — rewrite or reduce to `en.json`.
- README/info.md/TROUBLESHOOTING/CONTRIBUTING: drop the Medtronic footer + carelink install steps;
  `carelink.import_history` → `tandem.import_history`.
- New `docs/quality-gates.md` (declare current tier `bronze` + explicit gap to Platinum — the per-repo SoT oob links).
- ADRs: greenfield-V1 + Tandem-only scope; entity-golden tests (port mikrotik ADR-014); Platinum + null-not-guess;
  fail-visible-staleness (safety). Existing `docs/decisions/ADR-001..006` — ADR-001 (lts-data-paths) references the old
  `sensor.carelink_*` statistic ids; now correct by construction (`sensor.tandem_*`) — update it.
- `docs/data-schema.md` provenance table (field → API/Computed → surfaced), cite-or-null.
- Delete `docs/upstream-review-2026-03-12.md`; rewrite `docs/internal/hacs-default-submission.md` for the `tandem` resubmission.
- Regenerate sensor docs: `python scripts/generate_sensor_docs.py` (path already fixed to tandem).

## oob governance (owner-key — maintainer said "I'll onboard in a local session")
- Pointer installed: `docs/internal/oob-standards-pointer.md` (**gitignored**, slug `tandem`).
- Declaration drafted at `/workspace/oob/registry/standards-intake/STANDARDS-tandem-2026-07-10.md` (GREY, **uncommitted**
  in the oob clone — not pushed; oob push = operator Decide #5).
- **Owed:** `tandem` slug + `mailbox/to-tandem/` don't exist on oob `main` yet (onboarding step 3); relay ack pending.

## Watch-outs
- Statistic ids are now `sensor.tandem_*` by construction (old double-prefix bug gone) — don't reintroduce a hardcoded prefix.
- Coverage low spots the goldens haven't fully covered: `config_flow.py` (~61%) — reauth/reconfigure branches.
- The `strings.json` staleness will fail hassfest — fix in P5 before running `python -m script.hassfest` or the HACS action.
