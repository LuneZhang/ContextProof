---
name: context-proof
description: Audit and benchmark repository-level AI coding-agent context files with deterministic evidence. Use when an agent needs to evaluate AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, MCP notes, or other coding-agent instructions; detect risky, vague, duplicated, oversized, or contradictory rules; optionally generate a generic starter candidate only when explicitly requested; or summarize recorded agent benchmark runs across variants such as none, current, native-init, and contextproof-minimized.
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
   python scripts/contextproof.py audit /path/to/repo --pr-comment
   ```

   If the `contextproof` CLI is already installed, this equivalent command is
   also acceptable:

   ```bash
   contextproof audit /path/to/repo --pr-comment
   ```

3. Review the generated files under `/path/to/repo/.contextproof/`:

   - `report.json`
   - `report.md`
   - `pr-comment.md`
   - optional `context.min.md`, only when the user explicitly requests a generic starter candidate
   - optional `minimize-rationale.md`, only when `context.min.md` is generated

4. Report the static score, confidence state, critical/high findings, evidence,
   and generated file paths.

5. If the user explicitly asks for a minimized candidate, rerun audit with
   `--minimize`. Treat `context.min.md` as a generic candidate only. Do not
   overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or other
   context files unless the user explicitly asks.

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
- Do not present deterministic findings as a project-specific rewrite plan.
