---
name: context-proof
description: Audit, minimize, and benchmark repository-level AI coding-agent context files with deterministic evidence. Use when an agent needs to evaluate AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, MCP notes, or other coding-agent instructions; reduce token waste; detect risky or contradictory rules; generate a lean context candidate; or summarize recorded agent benchmark runs across variants such as none, current, native-init, and contextproof-minimized.
---

# ContextProof

## Purpose

Treat coding-agent context as testable infrastructure. Prefer deterministic
checks and measured run data over subjective judgment. Do not claim a context
improves agent performance unless benchmark evidence supports that claim.

## Primary Workflow

1. Identify the repository to audit. Use the current working directory unless
   the user gives another path.

2. Run the bundled deterministic runner from this skill folder:

   ```bash
   python scripts/contextproof.py audit /path/to/repo --pr-comment --minimize
   ```

   If the `contextproof` CLI is already installed, this equivalent command is
   also acceptable:

   ```bash
   contextproof audit /path/to/repo --pr-comment --minimize
   ```

3. Review the generated files under `/path/to/repo/.contextproof/`:

   - `report.json`
   - `report.md`
   - `pr-comment.md`
   - `context.min.md`
   - `minimize-rationale.md`

4. Report the static score, confidence state, critical/high findings, and the
   generated file paths.

5. Treat `context.min.md` as a candidate only. Do not overwrite `AGENTS.md`,
   `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or other context files unless the
   user explicitly asks.

## Benchmark Runs

If recorded benchmark runs exist, summarize them:

```bash
python scripts/contextproof.py summarize-runs /path/to/runs.jsonl --md-out /path/to/repo/.contextproof/benchmark-summary.md
```

Read `references/benchmark-design.md` before designing or changing benchmark
inputs.

## Evidence Model

- Static hygiene: deterministic scan and six-dimension score for
  discoverability, actionability, minimality, consistency, safety, and workflow
  fit.
- Behavioral evidence: recorded agent runs across variants such as `none`,
  `current`, native `/init`, and `contextproof-minimized`.

Read `references/scoring-rubric.md` before changing scoring weights or severity
levels. Read `references/context-antipatterns.md` when explaining findings.

## Output Policy

- Lead with static score, confidence state, and critical/high findings.
- Distinguish static risk from measured benchmark outcomes.
- Avoid claiming performance improvement unless behavioral run data supports it.
- Prefer small, concrete context edits to broad rewrites.
