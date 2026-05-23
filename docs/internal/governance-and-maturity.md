# Governance & Tooling Maturity — Standing Reference

Created 2026-05-23. The standing reference for how this repo manages agent context, prevents
scope/context drift, and raises tooling maturity. Recommendations are grounded in the Claude Code
Ultimate Guide (Florian Bruniaux) and the operator's own scope-drift protocol. CLAUDE.md holds the
*binding rules*; this doc holds the *rationale and roadmap* (per the guide's rules-vs-reference split).

> Warrant: `ISS-260523-claude-md-context`. Source protocol: `the-balcony/CLAUDE.md`,
> `gedcom-tree-parser/CLAUDE.md`. Guide: https://cc.bruniaux.com/guide/

---

## 1. Scope-drift protocol (governance — binding)

Codified in root `CLAUDE.md` §"Scope Discipline — Scope Warrants". Summary:

- Triggered change classes require an **accepted `ISS-YYMMDD-<topic>` warrant before work begins**;
  commits reference `Resolves: ISS-…`.
- Triggered: new top-level dir / new `docs/` subdir; new filetype or convention; **any tooling
  addition** (CI/Actions, linters, generators, hooks, dependency manifests, `manifest.json`
  requirements); new HA platform file; decoder without fixture; manifest `domain`/`version` change;
  off-list commit type.
- In-scope by default: resolving an accepted issue; updating ISSUES/CHANGE-REGISTER; typo/wording;
  status-table updates.
- **Ambiguous → treat as triggered and ask.** A polished result does not excuse a missing warrant.

This exists because the most damaging failures here have been *silent permanence*: a change made
"temporarily" that was never reverted (see the staleness bypass, ISS-260523-staleness-dead-code,
live ~2.5 months) and *scope creep mid-session* (writing files without a warrant).

## 2. Context-engineering rules (from the Ultimate Guide)

| Rule | Why | Source |
|---|---|---|
| All CLAUDE.md layers combined **4–8KB**; root **< 200 lines** | Adherence drops sharply past 400 lines; ~95% ≤100 lines → ~45% at 600+ | [context-engineering](https://cc.bruniaux.com/guide/ultimate-guide/03-memory-files/) |
| **150-instruction ceiling** — rule quality beats quantity | Beyond ~150 rules, models selectively ignore; attention diffuses | guide §2 |
| **Productive altitude** — capture decisions the model would make differently without the rule. Cut aspirational ("write clean code") and mechanical ("2-space indent" → linter) | Vague rules pass through unchanged; mechanical rules belong in ruff/editorconfig | [Goldilocks](https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/guide/core/context-engineering.md) |
| **Path-scoping via `@imports`** — load subsystem rules only when in that subsystem | 40–50% always-on context reduction with no loss of coverage | guide §4 |
| **Continuous Context Update** — distil mid-session discoveries into CLAUDE.md, not just handoffs | Handoffs are reasoning noise; CLAUDE.md is synthesis that persists | guide §3 |
| **MECW ~92% of advertised window** (~150K before rot on a 200K model) | n² attention scaling is structural; a lean 128K beats a stale 1M | guide §2 |
| **Agents = context isolation, not personas** | Use scoped passes (security, perf), not job-titled "teams" | guide §2 |

How this repo applies them: root `CLAUDE.md` (~180 lines, productive-altitude) + 3 path-scoped
modules (`custom_components/carelink/`, `tests/`, `.github/workflows/`) + this reference for depth.

## 3. Drift-protection mechanisms (recommended, each needs its own warrant to build)

1. **CI drift-check workflow** (`ISS-260523-ci-drift-check`) — adapt the guide's `ci-drift-check.yml`:
   weekly + on-change checks for CLAUDE.md size, broken `@import`s, freshness; auto-opens an issue
   labelled `ai-context,maintenance`. Thresholds: `MAX_LINES=200`, `WARN_LINES=160`. **Trigger: Actions addition.**
   Ref: https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/examples/context-engineering/ci-drift-check.yml
2. **Repo-aware session-start signal** (`ISS-260523-session-start-signals`) — extend the `focus-brief`
   SessionStart hook to read this repo's `docs/ISSUES.md` (Active count) and `docs/CHANGE-REGISTER.md`
   (In-Review rows). Currently it only matches the config repo's `DEPLOYMENT-REGISTRY.md`. **Trigger: tooling/hook.**
3. **Global allowlist prune + credential rotation** (`ISS-260523-allowlist-prune`) — `~/.claude/settings.json`
   has ~700 one-off allow entries (should generalise to ~50 verbs), **zero `deny` rules**, and **inlined
   live tokens** (GitHub PAT, Gitea, SonarCloud, Authentik, Proxmox). Add Layer-1 `deny`
   (`.env*`, `**/*.pem`, `**/*.key`, `**/credentials*.json`, `**/.ssh/id_*`). **Security-sensitive — rotate
   tokens regardless of when the prune lands.** Ref: [MCP secrets](https://cc.bruniaux.com/guide/ultimate-guide/08-mcp/).

## 4. Maturity roadmap (warrant queue)

Order is the operator's call. None proceed without an accepted warrant.

| Warrant | Scope | Class |
|---|---|---|
| `ISS-260523-protocol-adoption` | ✅ done — protocol in CLAUDE.md + this doc | governance |
| `ISS-260523-ci-drift-check` | CI drift workflow | Actions |
| `ISS-260523-session-start-signals` | repo-aware SessionStart hook | hook |
| `ISS-260523-allowlist-prune` | global allowlist prune + `deny` + token rotation | tooling/security |
| `ISS-260523-v2-domain-rename` | `carelink`→`tandem_source`, remove legacy Medtronic, brands PR, migration guide, ADR — unblocks HACS PR #6316 | domain change (ADR) |

## 5. Open correctness issues found alongside (audit 2026-05-23)

Tracked separately in ISSUES.md; listed here so governance work doesn't lose sight of them:
`ISS-260523-staleness-dead-code` (🔴 patient-safety, live), `ISS-260523-stats-hourly-collapse` (🔴),
`ISS-260523-carelink-error-swallow` (🔴), `ISS-260523-audit-moderates` (🟡 rollup).
