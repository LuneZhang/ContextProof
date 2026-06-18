---
name: context-proof
description: Audit, optimize, and benchmark repository-level AI coding-agent context files with deterministic evidence. Use when an agent needs to evaluate or improve AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, MCP notes, saved /init briefs, or other coding-agent instructions; detect risky, vague, duplicated, oversized, or contradictory rules; generate safe optimized candidate drafts under .contextproof/candidates; compare original context against candidates; or summarize recorded agent benchmark runs across variants such as none, current, native-init, and contextproof-reviewed.
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

## Primary Workflow: Audit

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

## Optimization Workflow

Use this workflow when the user asks to optimize, tighten, reduce, improve, or
rewrite agent context.

1. Read `references/context-optimizer.md` and
   `references/optimization-checklist.md`.

2. Run the audit workflow first and read the findings.

3. Pick the source context file that should be optimized. If multiple files
   overlap, optimize one clear candidate first unless the user asks for a
   migration pass.

4. Write the optimized candidate under `.contextproof/candidates/`. Preserve
   source filenames when possible, for example
   `.contextproof/candidates/AGENTS.contextproof.md`.

5. Do not overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or
   other source context files unless the user explicitly approves after seeing
   the candidate and comparison report.

6. Compare the original and candidate:

   ```bash
   python scripts/contextproof.py compare-context /path/to/source/AGENTS.md /path/to/repo/.contextproof/candidates/AGENTS.contextproof.md
   ```

   If the installed CLI is available:

   ```bash
   contextproof compare-context /path/to/source/AGENTS.md /path/to/repo/.contextproof/candidates/AGENTS.contextproof.md
   ```

7. Report the candidate path, score delta, estimated token delta, resolved
   findings, introduced findings, preservation warnings, regression flags, and
   generated candidate report path.

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

## Optimizer Prompt Benchmarks

When comparing optimizer prompt variants, use the scenario corpus and candidate
outputs:

```bash
python scripts/contextproof.py benchmark-optimizer /path/to/repo/examples/scenarios \
  --prompt-variant baseline \
  --jsonl-out /path/to/repo/.contextproof/optimizer-runs.jsonl \
  --md-out /path/to/repo/.contextproof/optimizer-summary.md
```

The runner does not call an LLM. It records results for candidates already
written by the active coding agent, so prompt variants can be compared on the
same fixtures without guessing.

## Evidence Model

- Static hygiene: deterministic scan and six-dimension score for
  discoverability, actionability, minimality, consistency, safety, and workflow
  fit.
- Behavioral evidence: recorded agent runs across variants such as `none`,
  `current`, native `/init`, and `contextproof-reviewed`.

Read `references/scoring-rubric.md` before changing scoring weights or severity
levels. Read `references/context-antipatterns.md` when explaining findings.
Read `references/context-optimizer.md` before drafting optimized context.

## Output Policy

- Lead with static score, confidence state, and critical/high findings.
- Distinguish static risk from measured benchmark outcomes.
- Avoid claiming performance improvement unless behavioral run data supports it.
- Do not present deterministic findings alone as proof that a rewrite is better.
- For optimization requests, provide a candidate and compare it against the
  original. Treat regression flags as blockers until reviewed.
