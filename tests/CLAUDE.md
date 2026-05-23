# Path-scoped rules — `tests/`

Loaded when editing tests. Inherits root `CLAUDE.md`.

## Running tests

- Canonical: `pytest tests/ -v` (full suite — 645+ tests). Windows wrapper: `run-tests.cmd`. CI uses a python 3.13 devcontainer image.
- Config: `pytest.ini` — `asyncio_mode = auto`, `testpaths = tests`, `pythonpath = tests`. Don't add `-k`/`--ignore` shortcuts to committed config.
- **Avoid ad-hoc one-file `pytest -k ...` / `ruff format <file>` variants in commits** — each new shell shape spawns a permission prompt that accumulates in the global allowlist. Use the canonical invocations.

## How to write tests here

- **Use real HA fixtures, don't mock the core or the DB.** `pytest-homeassistant-custom-component` provides `hass`; use `MockConfigEntry`. Mock the **network layer (httpx) only**. Mock/prod divergence has caused real misses.
- **Decoder tests must assert against captured payloads, not encoder round-trips.** `test_expanded_data.py` currently packs events with the same offsets it reads back — that cannot catch an offset regression. A real golden fixture is the fix (ISS-260523-audit-moderates). The one real capture is `tests/fixtures/known_good_api_response.json` (Carelink JSON) — a sanitised Tandem binary blob is still needed.
- **Cover error paths, not just happy paths**: auth failure, malformed/short payload, stale data, partial data, network error → `UpdateFailed`.
- **Don't rename a test to make a bypass pass.** ISS-260523-staleness-dead-code happened partly because `unavailable_when_stale` tests were renamed to `shows_last_value_when_stale` and re-asserted — the suite stayed green while documented behavior vanished. If behavior changes, change the code or file an issue; don't quietly invert the assertion.

## Coverage

- Project gate: ≥70% (SonarCloud measures project-wide). `tandem_api.py` is individually under-covered (~47%, ISS-005) despite being the highest-risk file — add file-level coverage when touching it.
