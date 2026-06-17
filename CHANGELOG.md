# Changelog

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
