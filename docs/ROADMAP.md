# Roadmap

## V0.1 Core

Status: complete.

- Deterministic static audit.
- Local JSON and markdown reports.
- Local PR-comment markdown.
- Minimal context candidate generation.
- Benchmark JSONL summary.
- Portable `context-proof` skill.
- Compatibility docs for Codex, Claude Code, OpenCode, and generic agents.

## V0.2 Benchmark Evidence

- Paired benchmark grouping.
- Directional and supported evidence states.
- Baseline comparison across `none`, `current`, `native-init`, and
  `contextproof-minimized`.
- Better uncertainty reporting.

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
- Minifier regression tests.
- Optional LLM advisory rewrites that never replace deterministic scoring.
