---
name: context-proof
description: Audit and benchmark repository-level AI coding-agent context files with deterministic evidence. Use when an agent needs to evaluate AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, MCP notes, or other coding-agent instructions; detect risky, vague, duplicated, oversized, or contradictory rules; optionally generate a generic starter scaffold only when explicitly requested; or summarize recorded agent benchmark runs across variants such as none, current, native-init, and contextproof-reviewed.
---

# ContextProof

## Purpose

Treat coding-agent context as testable infrastructure. Prefer deterministic
checks and measured run data over subjective judgment. Do not claim a context
improves agent performance unless benchmark evidence supports that claim.

## Scope

Audit Markdown that is loaded as coding-agent context, including `AGENTS.md`,
`CLAUDE.md`, `GEMINI.md`, `.cursor/rules`, `SKILL.md`, MCP notes, agent notes,
and `/init` output only after it has been saved as a persistent context file.

Do not treat ordinary README files, design docs, or one-off chat prompts as
audit targets unless they are actually injected into agent context.

## Primary Workflow

1. Identify the repository to audit. Use the current working directory unless
   the user gives another path.

2. Run the bundled deterministic runner from this skill folder:

   ```bash
   python scripts/contextproof.py audit /path/to/repo --pr-comment
   ```

   For a fresh repository, add `--project-mode new_project`. For migrations
   between agents or stacks, add `--project-mode migration_project`.

   If the `contextproof` CLI is already installed, this equivalent command is
   also acceptable:

   ```bash
   contextproof audit /path/to/repo --pr-comment
   ```

3. Review the generated files under `/path/to/repo/.contextproof/`:

   - `report.json`
   - `report.md`
   - `pr-comment.md`
   - optional `context.min.md`, only when the user explicitly requests a generic starter scaffold
   - optional `minimize-rationale.md`, only when `context.min.md` is generated

4. Report the static score, confidence state, critical/high findings, evidence,
   and generated file paths.

5. When reviewing a branch or PR, use `--changed-against` if the user provides
   a base ref/range. Use `--baseline` if the user provides a previous
   `.contextproof/report.json`.

6. If the user explicitly asks for a starter scaffold, rerun audit with
   `--minimize`. Treat `context.min.md` as a generic starter only. Do not
   overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or other
   context files unless the user explicitly asks.

## Benchmark Runs

If recorded benchmark runs exist, summarize them:

```bash
python scripts/contextproof.py summarize-runs /path/to/runs.jsonl --md-out /path/to/repo/.contextproof/benchmark-summary.md
```

To merge those runs into the main audit report:

```bash
python scripts/contextproof.py audit /path/to/repo --runs /path/to/runs.jsonl --pr-comment
```

Read `references/benchmark-design.md` before designing or changing benchmark
inputs.

## Evidence Model

- Static hygiene: deterministic scan and six-dimension score for
  discoverability, actionability, minimality, consistency, safety, and workflow
  fit.
- Behavioral evidence: recorded agent runs across variants such as `none`,
  `current`, native `/init`, and `contextproof-reviewed`.

Read `references/scoring-rubric.md` before changing scoring weights or severity
levels. Read `references/context-antipatterns.md` when explaining findings.

## Output Policy

- Lead with static score, confidence state, and critical/high findings.
- Distinguish static risk from measured benchmark outcomes.
- Avoid claiming performance improvement unless behavioral run data supports it.
- Do not present deterministic findings as a project-specific rewrite plan.
