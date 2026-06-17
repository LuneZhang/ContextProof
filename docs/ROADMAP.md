# Roadmap

## V0.1 Core

Status: complete.

- Deterministic static audit.
- Local JSON and markdown reports.
- Local PR-comment markdown.
- Optional generic context starter candidate generation.
- Benchmark JSONL summary.
- Portable `context-proof` skill.
- Compatibility docs for Codex, Claude Code, OpenCode, and generic agents.

## V0.1.1 Adoption Hardening

Status: complete.

- Skill-first README.
- Chinese README.
- Demo fixture for a flawed agent context.
- Agent-specific usage prompts.
- Refined reports around deterministic issue detection, evidence, confidence,
  and severity instead of rewrite planning.

## V0.2 Benchmark Evidence

Status: complete.

- Paired benchmark grouping.
- Directional and supported evidence states.
- Baseline comparison across `none`, `current`, `native-init`, and
  `contextproof-reviewed`.
- Better uncertainty reporting.
- `audit --runs` support for merging behavioral evidence into static reports.

## V0.3 CI And Review UX

- GitHub Action packaging.
- Optional PR comment posting.
- Score trend reports.
- Comment-only default with explicit opt-in gates.

## V0.4 Agent Baselines

- Helpers for collecting native `/init` outputs.
- Existing-project and new-project scenario fixtures.
- Agent-specific adapters where stable APIs exist.

## V0.5 Optimization Loop

- Fixture-driven scorer calibration.
- Generic starter-candidate regression tests.
- Optional LLM advisory rewrites that never replace deterministic scoring.
