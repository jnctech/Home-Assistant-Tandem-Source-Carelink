# HACS Default Store Submission — PR body

Use this as the PR body when submitting to https://github.com/hacs/default (category: integration).

---

## Repository

`jnctech/ha-tandem-pump` — domain `tandem`, **Tandem t:slim Pump**.

## What this integration is

The only Home Assistant integration for the **Tandem t:slim X2** insulin pump. It authenticates to
the **Tandem Source** cloud (OIDC/PKCE, US + EU regions) and surfaces CGM readings, insulin-on-board,
Control-IQ status, pump battery, alerts, settings, and long-term statistics — no extra hardware.

## History (why the domain looks new)

This repository began as a fork of [yo-han/Home-Assistant-Carelink](https://github.com/yo-han/Home-Assistant-Carelink)
(Medtronic CareLink). A prior submission under the `carelink` domain was **rejected** — the domain did
not match the integration's purpose, and it still carried a Medtronic path and a Nightscout uploader.

**v1.0.0 is a greenfield, Tandem-only rewrite** (see `docs/decisions/ADR-007`): the Medtronic and
Nightscout code is removed, the domain is `tandem`, and the integration is restructured to the modern
HA layout (thin `__init__.py` + `coordinator.py` + `entity.py` + declarative `*_types.py` +
`diagnostics.py`). It is a single-purpose integration for one device family.

## HACS / hassfest compliance

- `custom_components/tandem/manifest.json` — `domain`, `name`, `version` (1.0.0), `documentation`,
  `issue_tracker`, `codeowners`, `config_flow: true`, `iot_class: cloud_polling`, `quality_scale`.
- `hacs.json` at repo root; `info.md` rendered in HACS.
- Config flow (single step) + reauth + reconfigure; diagnostics; a data-stale health binary_sensor.
- Brand assets: submit `icon.png` / `logo.png` to [home-assistant/brands](https://github.com/home-assistant/brands)
  under `custom_integrations/tandem/` (required for the default store).

## Engineering

- 370+ tests (`pytest` + `pytest-homeassistant-custom-component`), 88% coverage, syrupy entity-goldens.
- Ruff (lint+format), Bandit, gitleaks, hassfest + HACS validation, SonarCloud, OpenSSF Scorecard in CI.
- Reverse-engineered Tandem Source binary event protocol (30+ event decoders); multi-CGM (Dexcom G6/G7,
  Libre 2). See `docs/internal/tandem-source-api-binary-events.md`.
- Quality tier + Platinum gap tracked in `docs/quality-gates.md`.

## Pre-submission checklist

- [ ] Brand assets merged in `home-assistant/brands` for domain `tandem`.
- [ ] A tagged GitHub release exists (HACS installs from releases).
- [ ] `hassfest` + `hacs/action` green on the default branch.
