# Changelog

## 0.6.0

- Added the one-prompt product workflow with `prepare-workflow`, which
  discovers agent context, audits it, classifies the scenario, routes the
  optimizer, and writes `.contextproof/workflow.md`.
- Added `discover-context` for explaining which repository Markdown files are
  in scope as agent-facing context and warning on README-only repositories.
- Added `review-candidate`, a user-facing candidate adoption report that puts
  unsafe regressions, removed or negated validation commands, removed path
  anchors, new critical/high issues, and overcompression before score deltas.
- Added `scripts/acceptance_v06.py` and moved `make acceptance` to the v0.6
  acceptance flow while keeping v0.5 acceptance as a release sub-check.
- Updated the standalone skill runner, README, Chinese README, usage docs, and
  skill metadata around the one-prompt workflow.
- Kept gold evaluation, scorer calibration, optimizer benchmark, and
  acceptance scripts as maintainer-only development tools.
- Package and skill metadata are `0.6.0`; report schema remains `0.5.0`.

## 0.5.1

- Reworked the README and Chinese README around a shorter skill-first adoption
  path: copy one prompt into a coding agent, install the skill, and review
  `.contextproof/` outputs.
- Compressed `skill/context-proof/SKILL.md` so normal invocations focus on the
  user workflow, while maintainer-only gold, benchmark, calibration, and
  acceptance commands are clearly separated.
- Added `docs/CAPABILITY_BOUNDARIES.md` to define the core user loop,
  maintainer-only loop, size profile, simplification rules, and guardrails.
- Kept package and skill metadata at `0.5.1`; report schema remains `0.5.0`
  because no output schema changed.

## 0.5.0

- Added gold/reference candidates for all eight built-in agent-context
  scenarios.
- Added `evaluate-gold` for deterministic source-vs-candidate-vs-gold
  evaluation, including preservation, unsafe regression, and overcompression
  checks.
- Extended optimizer benchmarks with gold alignment verdicts, scores, unsafe
  regression counts, overcompression counts, and missing-preservation counts.
- Added `calibrate-scorer` and a scorer calibration JSONL fixture set for
  checking expected issue ids, severity, dimensions, and score buckets.
- Added `scripts/acceptance_v05.py` and `make acceptance` as the repeatable
  v0.5 acceptance flow.
- Updated the standalone skill runner and docs so the skill workflow is now
  audit -> classify/route -> draft candidate -> compare -> evaluate gold when a
  scenario fixture exists -> benchmark.

## 0.4.0

- Added scenario classification for agent-facing context with
  `classify-context`.
- Added `route-optimizer`, which selects a scenario-specific optimizer template
  and writes `.contextproof/optimizer-instructions.md`.
- Added optimizer templates for new-project `/init` briefs, existing project
  rules, multi-agent migrations, workflow SOPs, safety-sensitive context, and
  token-heavy context.
- Extended optimizer benchmark rows and summaries with classified scenario
  routes, selected templates, and classification match rates.
- Updated skill workflow and documentation so optimization follows
  classify -> route -> draft candidate -> compare.

## 0.3.0

- Repositioned ContextProof around the core agent-context optimization loop:
  audit source context, draft safe candidates, compare candidates, and benchmark
  prompt variants.
- Added `compare-context` for original-versus-candidate evaluation with score
  delta, token delta, resolved and introduced findings, preservation checks,
  and regression flags.
- Added `benchmark-optimizer` for recording optimizer prompt-variant results
  across scenario fixtures as JSONL and markdown summaries.
- Added a V0.3 scenario corpus covering overbroad context, conflicting context,
  saved `/init` briefs, multi-agent migration, unsafe automation, missing
  validation criteria, misplaced general documentation, and token-heavy
  monorepo context.
- Added optimizer prompt references and an explicit skill workflow that writes
  candidates under `.contextproof/candidates/` without overwriting source
  context files.
- Updated English and Chinese documentation to make context optimization the
  primary user workflow.

## 0.2.1

- Added changed agent-context file detection from local git state or a git ref/range.
- Added baseline report comparison for score and finding deltas.
- Improved PR comment output for changed context files and baseline deltas.
- Added a more realistic team-agent-context demo fixture.
- Updated the GitHub workflow template to run on agent-context file changes.

## 0.2.0

- Added paired benchmark grouping and comparison summaries.
- Added benchmark evidence states: insufficient, mixed, directional, and supported.
- Added `audit --runs` to merge recorded behavioral evidence into audit reports.
- Added canonical `existing_project`, `new_project`, and `migration_project` modes.
- Renamed the benchmark improvement variant to `contextproof-reviewed`.
- Documented ContextProof's core scope as agent-facing Markdown context, not arbitrary Markdown.
- Refined README positioning around a copy-and-run audit loop and moved advanced features out of the primary path.

## 0.1.1

- Added a skill-first usage guide and Chinese README.
- Added a demo fixture for intentionally flawed agent context.
- Added agent-specific usage prompts.
- Refined reports around deterministic issue detection, evidence, confidence,
  and severity instead of rewrite planning.
- Kept CLI behavior as the deterministic runner behind the skill workflow.

## 0.1.0

- Added the portable `context-proof` agent skill.
- Added deterministic static audits for repository-level coding-agent context.
- Added local JSON, markdown, and PR-comment report generation.
- Added optional generic context starter candidate generation.
- Added benchmark JSONL summary support.
- Added report and benchmark run JSON schemas.
- Added optional CLI entry point for CI and manual fallback use.
