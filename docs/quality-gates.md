# Quality Gates — Tandem t:slim integration

The per-repo source of truth for what this integration enforces and the tier it
targets. (oob estate register links here; `STANDARD-code-quality-2026-07-04` §2.)

## Integration Quality Scale — current tier and the gap to Platinum

**Current: `bronze`** (declared in `manifest.json`). The greenfield V1 restructure
put the Gold/Platinum *structure* in place; the remaining Platinum technical rules
are tracked below. We **aim Platinum** and under-tier honestly rather than claim a
tier we don't meet.

| Platinum technical rule | State | Gap / plan |
|---|---|---|
| **async-dependency** (the API library is asyncio-based) | ✅ met | `tandem_api.py` is in-repo and fully `httpx`-async. |
| **inject-websession** (reuse HA's managed client) | ❌ gap | `TandemSourceClient` builds its own `httpx` client; switch to `homeassistant.helpers.httpx_client.get_async_client(hass)`. |
| **strict-typing** (fully typed; mypy-strict) | ◐ partial | House-layout modules typed; `coordinator.py` / `tandem_api.py` are `ignore_errors` in `pyproject.toml` pending their typing pass. |

Gold completeness already present: config flow + reauth + reconfigure, diagnostics
(`diagnostics.py`), entity metadata (device/units/state_class), a data-stale health
`binary_sensor`, and comprehensive docs. Entity translations are the main Gold nicety
still to add.

## Mechanical gates (CI + local)

| Gate | Tool | Where |
|------|------|-------|
| Lint + format | Ruff | `pyproject.toml`; `.github/workflows/ci.yml`, `.gitea/workflows/ci.yml` |
| Types | mypy (strict, incremental) | `pyproject.toml` `[tool.mypy]` |
| Tests | pytest + `pytest-homeassistant-custom-component` | `pytest.ini` |
| Coverage | `fail_under = 80` | `pyproject.toml` `[tool.coverage.report]` |
| Security | Bandit + gitleaks | `bandit.yaml`, `.gitleaks.toml`, CI |
| HA validity | hassfest + HACS action | `.github/workflows/validate.yml` |
| API drift | `scripts/check_api_drift.py` | `tests/test_api_drift.py` |
| Quality | SonarCloud (reliability/security/maintainability ≥ A) | `sonar-project.properties` |

## Toolchain baseline

- **HA 2026.2.x on Python 3.13** — the last HA line runnable on 3.13 (2026.3+ requires
  Python 3.14.2). Pins in `requirements.txt`. CI should run a 3.13 (and, when the runner
  supports it, 3.14) matrix.

## Test taxonomy (ADR-009)

- **L0 — logic unit tests:** parsing / compute / staleness, against the coordinator directly.
- **L1 — entity goldens:** `tests/test_sensor_golden.py` via `snapshot_platform` (syrupy
  `.ambr`), **paired with load-bearing invariant asserts** — a re-blessed-wrong snapshot is
  caught by the invariant (`STANDARD-code-quality` §1). First bless reviewed by hand, never
  blind `--snapshot-update`.
- **L2 — flow tests:** config/reauth/reconfigure via `MockConfigEntry`.

## Governing rules

- **cite-or-null** — every factual claim cites its source (`file:line`, tool output) or is
  marked UNVERIFIED; unknowns are reported, never guessed.
- **null-not-guess (code standard)** — a missing/malformed API field resolves to
  `None`/`unavailable` via `.get()`, never a fabricated default. For a glucose/insulin
  integration a fabricated value is a safety hazard.
- **fail-visible staleness (safety, ADR-008)** — stale decision-input sensors go
  unavailable; `binary_sensor.tandem_data_stale` is the named health surface.
