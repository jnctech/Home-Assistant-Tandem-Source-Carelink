# Tandem t:slim Pump — Home Assistant Integration (ha-tandem-pump)

Project memory for Claude Code. Read at every session start. Source: `~/Code/hacs/Tandem-Source/Home-Assistant-Tandem-Source-Carelink`.

> This file is project-scope. Global rules live in `~/.claude/CLAUDE.md`; subsystem rules live in path-scoped modules (see §Path-Scoped Modules). Keep this file under 200 lines.

## Scope Discipline — Scope Warrants (read first)

Certain change classes require an **accepted `docs/ISSUES.md` entry — the "scope warrant" — *before* work begins.** The warrant is an `ISS-YYMMDD-<topic>` entry the operator has accepted. Commits acting on it reference `Resolves: ISS-YYMMDD-<topic>` in the body. **If you are about to make a triggered change and there is no accepted warrant, STOP and ask. If a change is ambiguous, treat it as triggered and ask.** Producing a polished result does not excuse skipping the warrant — order matters.

**Triggered (warrant required before any edit):**
- New top-level directory, or new `docs/` subdirectory outside the existing set (`internal/`, `decisions/`, `reviews/`).
- Introducing a filetype or convention not previously committed.
- **Any tooling addition:** CI config / GitHub Actions, linters, generators, pre-commit hooks, dependency manifests, `manifest.json` requirements.
- New HA platform file, new event-type decoder without an existing fixture, manifest `domain`/`version` change (see §STOP-and-ASK for the full integration-specific list).
- A commit message using a conventional-commit type outside `docs|feat|fix|refactor|chore|test`.

**In-scope by default (no warrant):**
- Code/test changes that resolve an already-accepted issue.
- Updating `docs/ISSUES.md` / `docs/CHANGE-REGISTER.md` to reflect work just done or to file/accept a warrant.
- Typo / wording fixes in committed prose; status-table updates.

Standing reference for governance + the maturity roadmap: `docs/internal/governance-and-maturity.md`.

## Stack

- HA custom_component, domain `carelink`, fork of upstream `noiwid/HAFamilyLink` (do not change upstream refs in docs unless explicitly asked).
- Python ≥ 3.13 in CI; HA min version per `manifest.json`.
- Two coordinators feed a single `coordinator.data` dict:
  - `TandemSourceClient` (`tandem_api.py`) — Tandem Source REST API, binary event payloads, 5-minute polling, staleness gate.
  - `CarelinkClient` (`api.py`) — Medtronic Carelink fallback for legacy users.
- Tests: pytest + `pytest-homeassistant-custom-component` (HA bootstrap fixtures). Local runner is `run-tests.cmd`; CI runs in a python 3.13 devcontainer image. Coverage target ≥ 70% per CI gate.
- Quality gates locally and in CI: `ruff check`, `ruff format --check`, `bandit -c bandit.yaml`, `gitleaks`, SonarCloud, OpenSSF Scorecard.

## Architecture decisions (the why)

- **One `coordinator.data` dict, two writers.** Both coordinators populate the same dict so a single sensor entity can resolve from either source. Mutation rules below are non-negotiable as a result.
- **Stale-data handling is currently BYPASSED in production (see ISS-260523-staleness-dead-code).** The design intent: a staleness threshold (now 6 h, was 30 min) turns glucose/insulin/basal/delta sensors `unavailable` while timestamp/serial/model/software stay available. In reality `sensor.py` `available` returns `super().available` only — `is_data_stale()` (`helpers.py`) runs but is wired to nothing except an INFO log (`__init__.py:1258`). This was a temporary "DIAGNOSTIC MODE" (PR #24, 2026-03-06) never reverted. Do not describe staleness as active until that issue is resolved.
- **Binary payload decoders are offset-sensitive.** `tandem_api.py` decodes Tandem Source events from raw bytes; offsets came from reverse-engineering, not a public contract. They are not stable across firmware. The `CartridgeFilled` regression (v1.5.0) was a 4-byte offset miss that returned `0.0` silently for months.
- **HACS submission constraint.** Repo is on `hacs/default` (PR #6316). HACS requires `==` exact-pinned requirements, `integration_type: hub`, reauth flow, `async_set_unique_id`, and OpenSSF Token-Permissions on workflows. Don't relax any of these without an ADR.
- **`__init__.py` is 2972 lines (known debt).** TandemCoordinator extraction tracked in ISSUES.md as a refactor — do not add new top-level helpers there; create a new module.

## Conventions (productive-altitude rules)

- **Never call `setdefault()` on `coordinator.data` or any nested dict on it.** Use `.get()` then explicit assignment. Mutation via `setdefault` caused the v1.0.0 "glucose graph spikes" regression where state replay overwrote real readings with `None`.
- **Auth errors raise `ConfigEntryAuthFailed`, not `UpdateFailed`.** Both `TandemAuthError` and `CarelinkClient.login() = False` must propagate as `ConfigEntryAuthFailed` so HA triggers the reauth flow. `UpdateFailed` silently retries forever.
- **Entity `unique_id` must include `config_entry.entry_id`.** Multi-entry setups (Tandem + Carelink in one HA instance) collide otherwise. See `helpers.py::build_unique_id`.
- **Sync I/O on the event loop is a bug.** Anything that opens a file (`_migrate_legacy_logindata`, fixture loaders called in setup) goes through `hass.async_add_executor_job(...)`.
- **Pinned requirements only.** `manifest.json` requirements use `==` exact versions (H-4). Don't loosen to `~=` or `>=`.
- **Imports add a sensor → add a fixture.** Any new event-type decoder in `tandem_api.py` ships with: (a) a hex-dump fixture under `tests/fixtures/`, (b) a test in `test_tandem_api.py` or `test_expanded_data.py`, (c) the offset table in `docs/internal/tandem-source-api-binary-events.md`. No fixture, no merge.
- **Don't mock the HA core or the database in tests.** Use `pytest-homeassistant-custom-component`'s `hass` fixture and real `MockConfigEntry`. Mock the *network* (httpx) only. This is a hard preference — mock/prod divergence has bitten before.
- **Sensor lists drift fast.** `const.py` is 1538 lines of sensor definitions; when adding/removing, update README + `info.md` sensor counts in the same PR (HACS docs gate).
- **No `--no-verify`, no skipped hooks, no `--no-gpg-sign`.** Local pre-commit hooks must pass. If a hook fails, fix the cause; don't bypass it.

## Path-Scoped Modules

Loaded on demand when files under these paths are in scope. Source these instead of duplicating the rules here.

@custom_components/carelink/CLAUDE.md
@tests/CLAUDE.md
@.github/workflows/CLAUDE.md

## Never Execute Without Approval

These actions need an explicit, in-turn user confirmation — a prior approval in the session does not carry forward.

- `gh release create`, `gh release edit`, `gh release delete` — releases are user-visible and downstream HACS users pick up immediately.
- `gh pr merge` on a PR targeting `master` or `develop` — branches are protected and CI is the gate; merge is the user's call.
- `git push --force` / `--force-with-lease` to any branch with an open PR or to `master`/`develop`/`main`.
- `gh pr close` / `gh issue close` on items the user didn't open this session.
- Any write to a live HA instance (`scp` into `/config/`, `ssh ... ha core restart`, edits to `.storage/`). The HA instance at `192.168.88.43` is the user's production diabetes monitoring; deploy via HACS update flow unless the user says otherwise.
- `gh repo edit`, `gh repo rename`, `git remote set-url` — repo identity changes break HACS users' update flow.
- Submitting or closing a PR on `hacs/default`.
- Bumping `manifest.json` `version` — release-coupled, owner approves.
- Removing or renaming an existing entity's `unique_id` — breaks every user's history.

## Always Require Before a PR

- `pytest tests/ -v` green (188+ tests; full suite, not subset).
- `ruff check custom_components tests` clean.
- `ruff format --check custom_components tests` clean.
- `bandit -c bandit.yaml -r custom_components/` clean.
- New code paths have tests (no merge of an untested coordinator branch).
- `docs/CHANGE-REGISTER.md` updated with a `CR-YYMMDD-<branch-slug>` entry.
- `docs/ISSUES.md` updated for any issue resolved or progressed.
- PR target confirmed (`develop` for features, `master` only for release branches and hotfixes).
- Manifest version is **not** bumped in feature branches — only in dedicated `release/x.y.z` branches.

## STOP-and-ASK Triggers

Stop and ask the user before any of these. No silent expansion of scope.

- New HA platform file (`number.py`, `switch.py`, etc.) — implies entity contract and HACS impact.
- New event-type decoder in `tandem_api.py` without an existing hex-dump fixture.
- New entry in `manifest.json` `requirements` — every dependency is HACS-reviewed surface.
- Adding `recorder` / `bluetooth` / other HA system dependencies to `after_dependencies`.
- Touching `homekit`, `zeroconf`, `dhcp` discovery blocks in `manifest.json`.
- Changing `domain` in `manifest.json` (catastrophic for existing users — entity registry break).
- Cherry-picking from upstream `noiwid/HAFamilyLink` — fork divergence is intentional and documented in CHANGE-REGISTER.
- Submitting an upstream PR (default PR target is always `jnctech` fork).
- Adding a new GitHub Actions workflow — must be SHA-pinned (OpenSSF) and have `permissions: {}` at top level.
- Disabling, downgrading, or skipping any pre-commit hook.

## Anti-Patterns

- **Ad-hoc shell variants in commits.** When iterating on `pytest -k ...` or `ruff format <one file>`, every shape difference triggers a new permission prompt that lands in the global allowlist. Use `run-tests.cmd` or `pytest tests/ -v` as the canonical invocations.
- **Inline tokens in code or settings.** All Sonar/Gitea/GitHub/Authentik/Proxmox tokens live in env vars; never literal in a `Bash(curl ... -H "Authorization: token xxx")` allow entry.
- **Generic agent personas as roles.** Pre-built agents (code-reviewer, simplifier, silent-failure-hunter) are scoped *passes*, not job titles. Use them when you need fresh context on a single concern, not to roleplay a team.
- **Treating handoffs as a substitute for CLAUDE.md updates.** Discoveries that affect future sessions go *here* (or in a path-scoped module), not just in the next handoff file.

## Session-End Hygiene

Before writing the handoff:

1. Did anything we discovered today belong in this file or a path-scoped module? Propose the edit, don't bury it in the handoff.
2. Did any pre-commit / CI gate get skipped or fail? If yes, surface in the handoff under "Outstanding".
3. Are there new untracked files in working tree that shouldn't be? Either commit them or `.gitignore` them — don't let them age.

## Reference Docs

- `docs/ISSUES.md` — active work, date-based IDs (`ISS-YYMMDD-<topic>`).
- `docs/CHANGE-REGISTER.md` — significant changes (`CR-YYMMDD-<branch-slug>`).
- `docs/decisions/` — ADRs (architecture decisions). New ADR required for: data-format changes, entity identity changes, API contracts, migrations.
- `docs/internal/tandem-source-api-binary-events.md` — binary event payload reference.
- Live HA SSH key for debugging logs only: `~/.ssh/ha_debug_ed25519` → `root@192.168.88.43`.
