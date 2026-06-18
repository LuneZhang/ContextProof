# TODO

This checklist tracks the current product route. ContextProof must stay focused
on one job: improving persistent Markdown context that coding agents actually
read.

## Product Essence

ContextProof is a coding-agent context optimization skill.

The target input is not arbitrary Markdown. The target input is Markdown that a
coding agent reads before or during code edits:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.cursor/rules/*`
- `.github/copilot-instructions.md`
- `SKILL.md`
- MCP notes
- saved `/init` repository briefs
- project-local agent rules for OpenCode, Codex, Claude Code, Cursor,
  Windsurf, Pi, and similar tools

The user should install the skill, then ask their coding agent to audit and
improve those files in natural language. The deterministic CLI is the runner
behind the skill, not the product's primary identity.

## V0.5.1 Definition Of Done

V0.5.1 is complete when ContextProof feels like a small, ready-to-use skill
instead of a pile of CLI commands:

- The README starts with one agent prompt and one install path.
- The Chinese README mirrors the same short adoption path.
- `SKILL.md` stays concise and points to references only when needed.
- Maintainer-only commands are clearly separated from the user workflow.
- Capability boundaries and size-control rules are documented.
- Package and skill metadata are `0.5.1`; report schema remains `0.5.0`.

## V0.5.1: Skill-First Adoption Polish

- [x] Rewrite README around the copy-into-agent prompt.
- [x] Rewrite Chinese README around the same usage path.
- [x] Compress `skill/context-proof/SKILL.md`.
- [x] Add `docs/CAPABILITY_BOUNDARIES.md`.
- [x] Keep gold, benchmark, calibration, and acceptance as maintainer flows.
- [x] Bump package and skill metadata to `0.5.1`.

## V0.5 Definition Of Done

V0.5 is complete when ContextProof can judge its own optimizer outputs against
curated references:

- All eight built-in scenarios have gold/reference candidates.
- `evaluate-gold` can distinguish true improvement from candidates that delete
  validation commands, path anchors, safety boundaries, or required project
  constraints.
- `benchmark-optimizer` reports gold alignment fields and route-level gold
  metrics.
- `calibrate-scorer` reports expected issue, severity, dimension, and score
  bucket mismatches on a focused calibration set.
- `make acceptance` runs the complete local v0.5 acceptance flow.
- The standalone skill runner supports the same commands as the package CLI.

## V0.5.0: Gold Candidates

- [x] Add `gold/AGENTS.gold.md` for:
  - [x] `existing-project-overbroad`
  - [x] `existing-project-conflicting`
  - [x] `new-project-init-brief`
  - [x] `multi-agent-migration`
  - [x] `unsafe-automation`
  - [x] `missing-validation-criteria`
  - [x] `misplaced-general-documentation`
  - [x] `token-heavy-monorepo`
- [x] Add v0.5 gold metadata to each `expected.json`.
- [x] Keep gold candidates as benchmark references, not user-project answers.

## V0.5 Gold Evaluation

- [x] Add `evaluate-gold SCENARIO_DIR CANDIDATE_PATH`.
- [x] Write `.contextproof/gold-evaluation.json`.
- [x] Write `.contextproof/gold-evaluation.md`.
- [x] Evaluate source vs candidate, source vs gold, and candidate vs gold.
- [x] Return verdicts for gold alignment, partial alignment,
  overcompression, unsafe regression, missing preservation, and not improved.
- [x] Detect deleted validation commands, risky shell regressions, and
  overcompressed candidates.

## V0.5 Benchmark Extension

- [x] Add gold fields to optimizer benchmark rows.
- [x] Add gold alignment, unsafe regression, overcompression, and
  missing-preservation counts to summaries.
- [x] Keep success criteria strict: no unsafe regression, no missing
  preservation, no critical/high finding growth, and gold alignment required
  when a scenario has a gold candidate.

## V0.5 Scorer Calibration

- [x] Add `examples/calibration/cases.jsonl`.
- [x] Add `calibrate-scorer`.
- [x] Report missing expected issues, unexpected issues, severity mismatches,
  dimension mismatches, score bucket mismatches, and failed cases.
- [x] Calibrate only rules needed for candidate evaluation.

## V0.5 Acceptance Flow

- [x] Add `scripts/acceptance_v05.py`.
- [x] Add `make acceptance`.
- [x] Verify tests, scenario integrity, classification routes, gold self
  evaluation, bad-candidate detection, optimizer benchmark, scorer calibration,
  standalone runner, self-audit, and file hygiene.
- [x] Use exit code 0 for pass, 1 for failed checks, 2 for fixture errors, and
  3 for internal errors.

## V0.5 Documentation And Release Hardening

- [x] Update README and Chinese README.
- [x] Update roadmap, TODO, usage docs, skill instructions, and reference docs.
- [x] Bump package, schema, skill metadata, and changelog to `0.5.0`.
- [x] Sync the package CLI into the standalone skill runner.
- [x] Add tests for gold evaluation, scorer calibration, benchmark gold fields,
  acceptance success path, and acceptance fixture-error path.

## Non-Goals

- [x] Do not create an industry template library.
- [x] Do not make CI or GitHub Actions the primary product loop.
- [x] Do not automatically replace user context files.
- [x] Do not claim improved coding-agent performance without behavioral runs.
- [x] Do not optimize ordinary project documentation unless it is actually
  injected into agent context.
