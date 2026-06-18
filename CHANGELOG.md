# Changelog

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
