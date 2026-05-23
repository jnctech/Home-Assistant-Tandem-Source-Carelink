# Path-scoped rules — `.github/workflows/`

Loaded when editing CI/CD. Inherits root `CLAUDE.md`. These are OpenSSF/HACS hard requirements — Scorecard regresses if broken.

## Workflows (9)

`ci.yml` (pytest/ruff/bandit), `validate.yml` (hassfest + HACS), `sonarcloud.yml`, `scorecard.yml` (OpenSSF), `dependency-review.yml`, `release.yml`, `conflicts.yml`, `lock.yml`, `stale.yml`.

## Hard rules

- **SHA-pin every action.** Use the full commit SHA, not a tag (`uses: actions/checkout@<sha>  # v4.x`). Dependabot (`github-actions` ecosystem, targets `develop`) keeps SHAs current. Tag refs are mutable → supply-chain risk → Scorecard Pinned-Dependencies failure.
- **Top-level `permissions: {}` on every workflow**, then grant the minimum at job level (e.g. `contents: read`, `contents: write` only on the release job). Don't add `checks: write` unless a step provably needs it (it was dropped from sonarcloud.yml deliberately).
- **New workflow → SHA-pinned + `permissions: {}` + add to this list.** This is a root STOP-and-ASK trigger.
- **`release.yml`**: `contents: write` lives at job level, not top level.
- Adding a GitHub Action dependency = new supply-chain surface; confirm before introducing.

## Gotchas

- Branch protection on `master`/`develop` requires the CI checks as the gate (PR-review requirement was removed — solo maintainer). Don't merge by bypassing checks.
- `gitea` remote runs an inner-loop CI mirror; GitHub Actions are the source of truth.
