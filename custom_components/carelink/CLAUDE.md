# Path-scoped rules — `custom_components/carelink/`

Loaded when editing integration source. Inherits root `CLAUDE.md`; these are subsystem specifics.

## Module map (and what NOT to grow)

- `__init__.py` (~2972 lines) — **god module, known debt.** Holds both coordinators, services, file I/O, `_parse_pump_events` (1466-2170, ~700 lines), `_import_statistics`. **Do not add new top-level helpers here.** New logic → new module (`tandem_coordinator.py` extraction is the tracked target).
- `tandem_api.py` (~1139) — `TandemSourceClient`, binary event decoders. Offset-sensitive (see root rules).
- `api.py` (~609) — legacy `CarelinkClient` (Medtronic). Slated for deprecation; don't invest here without asking.
- `const.py` (~1538) — `SENSORS` (Carelink) + `TANDEM_SENSORS`. Adding/removing a sensor → update README + `info.md` counts same PR.
- `nightscout_uploader.py` — `NightscoutUploader`, wired only when `nightscout_url`/`nightscout_api` config present (`__init__.py:372`, `:595`).

## Hard rules (regressions live here)

- **Never `setdefault()` on `coordinator.data` or nested dicts on it.** Use `.get()` + explicit assignment. Caused the v1.0.0 glucose-spike regression. (Note: `recent_data` input dict at `__init__.py:715` uses setdefault on the *input*, not output — order-dependent, fragile, don't copy the pattern.)
- **Binary decoder offsets are firmware-derived, not contractual.** Any new/changed offset or length in `tandem_api.py` ships with a captured (not encoder-synthesised) fixture + a value assertion. The `CartridgeFilled` 4-byte-offset bug returned `0.0` silently for months because tests round-tripped the same offsets.
- **Validate payload length before `struct.unpack_from`.** The `len(chunk) < EVENT_LEN` guard (`tandem_api.py:126`) is load-bearing — keep all offsets within the 16-byte payload window.
- **Auth failures raise `ConfigEntryAuthFailed`** (not `UpdateFailed`): `TandemAuthError` and Carelink `login()=False`. Network/fetch failures raise `UpdateFailed` — do **not** return `None` and let the caller treat it as empty (see ISS-260523-carelink-error-swallow, `api.py:178-185`).
- **`unique_id` includes `config_entry.entry_id`** (multi-entry safety) — `helpers.py`.
- **No sync I/O on the loop.** File reads, `_migrate_legacy_logindata` → `hass.async_add_executor_job(...)`.
- **Long-term statistics use 5-minute buckets with aggregation.** Carelink path is correct (`_import_sg_statistics`, `__init__.py:967`); the Tandem path currently rounds to the hour and overwrites (ISS-260523-stats-hourly-collapse, `__init__.py:2792`) — match the Carelink pattern when fixing.

## Known active correctness issues (don't reintroduce / mind when editing)

- Staleness gate is **bypassed in production** — `sensor.py` `available` ignores `is_data_stale()` (ISS-260523-staleness-dead-code). Don't describe it as active.
- Broad `except Exception` is common; most are deliberate per-item isolation. When adding one, log at `warning`+ and make sure it can't mask a decoder/data-shape regression as "no data."
