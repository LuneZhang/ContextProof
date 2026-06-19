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

## V0.6 Definition Of Done

V0.6 is complete when ContextProof's normal product workflow is simple enough
for a user to run through their coding agent without learning maintainer
commands:

- One natural-language prompt can start the skill workflow.
- ContextProof can discover likely agent-context files and explain scope.
- The user receives one coherent `.contextproof/` work packet: audit,
  classification, optimizer instructions, candidate path, and comparison.
- The active coding agent gets focused rewrite instructions without loading
  benchmark, gold, calibration, or acceptance material.
- Candidate comparison clearly blocks unsafe regressions, removed validation
  commands, negated validation commands, and lost project path anchors.
- Source context files are never overwritten by default.
- V0.5 acceptance remains green, and v0.6 adds checks for the one-prompt
  workflow and standalone skill runner parity.

## V0.6: Product/Development Separation

- [x] Add or maintain a product strategy document that separates:
  - [x] user-facing product loop
  - [x] maintainer development loop
  - [x] distribution track
- [x] Keep README and skill instructions focused on the user-facing loop.
- [x] Keep gold, calibration, benchmark, and acceptance commands in maintainer
  docs only.
- [x] Avoid presenting baseline experiments as a normal user feature.

## V0.6: Context Discovery

- [x] Add repository context discovery for supported agent-facing files:
  - [x] `AGENTS.md`
  - [x] `CLAUDE.md`
  - [x] `GEMINI.md`
  - [x] `.cursor/rules/*`
  - [x] `.github/copilot-instructions.md`
  - [x] `SKILL.md`
  - [x] MCP notes
  - [x] saved `/init` briefs
- [x] Report why each discovered file is in scope.
- [x] Warn, but do not fail, when only ordinary Markdown docs are found.
- [x] Add tests for root files, nested rule files, empty repositories, and
  ordinary README-only repositories.

## V0.6: One-Prompt Workflow Packet

- [x] Add a user-facing command or runner flow that performs:
  - [x] discover
  - [x] audit
  - [x] classify-context
  - [x] route-optimizer
  - [x] write optimizer packet
- [x] Write `.contextproof/workflow.md` with:
  - [x] selected source files
  - [x] primary scenario route
  - [x] candidate output path
  - [x] preserve list
  - [x] remove or tighten list
  - [x] validation and safety blockers
  - [x] exact next instruction for the active coding agent
- [x] Keep `.contextproof/workflow.md` concise enough to paste back into an
  agent conversation.
- [x] Add JSON output for machine-readable skill runner use.

## V0.6: Candidate Review UX

- [x] Consolidate comparison output into a user-readable summary.
- [x] Highlight blockers first:
  - [x] unsafe regression
  - [x] removed validation command
  - [x] negated validation command
  - [x] removed project path anchor
  - [x] new critical or high issue
  - [x] overcompression
- [x] Show score delta and token delta after blockers.
- [x] Make the adoption recommendation explicit:
  - [x] safe to consider
  - [x] review required
  - [x] do not adopt yet
- [x] Do not automatically write changes back to source context files.

## V0.6: Skill Hot-Path Size Control

- [x] Keep `skill/context-proof/SKILL.md` short and procedural.
- [x] Move detailed maintainer material out of the installed skill hot path.
- [x] Load scenario templates only after routing selects them.
- [x] Avoid adding agent-specific overlays unless they change file loading or
  invocation style.
- [x] Add a lightweight size check for the installed skill hot path.

## V0.6 Acceptance Flow

- [x] Keep all v0.5 acceptance checks passing.
- [x] Add v0.6 checks for:
  - [x] context discovery on fixture repositories
  - [x] one-prompt workflow packet generation
  - [x] workflow packet includes route, candidate path, and no-overwrite rule
  - [x] candidate review summary blocker ordering
  - [x] README-only repository warning behavior
  - [x] skill hot-path size limit
  - [x] standalone skill runner command parity
  - [x] no tracked `.contextproof/`, cache, or generated files
- [x] Exit codes should follow the existing acceptance convention:
  - [x] `0` for pass
  - [x] `1` for failed checks
  - [x] `2` for fixture or input errors
  - [x] `3` for internal exceptions

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
