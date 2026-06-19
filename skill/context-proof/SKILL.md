---
name: context-proof
description: Audit and optimize coding-agent context files such as AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, MCP notes, and saved /init briefs. Use to find vague, unsafe, contradictory, oversized, or hard-to-validate persistent instructions; route to a scenario template; draft candidates under .contextproof/candidates; compare candidate quality; or run maintainer benchmarks.
---

# ContextProof

## Purpose

Improve Markdown that is actually loaded into a coding agent's prompt context.
Do not use this skill as a general Markdown linter, README optimizer, CI
dashboard, or automatic rewrite tool.

## Scope

Use ContextProof for persistent agent-facing context:

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
- `.cursor/rules/*`, `.github/copilot-instructions.md`
- `SKILL.md`, MCP notes, agent notes
- saved `/init` repository briefs

Ignore ordinary README files, design docs, one-off chat prompts, and business
documentation unless the user says they are injected into agent context.

## Default User Workflow

When the user asks to audit, tighten, optimize, reduce, or improve agent
context:

1. Prepare the workflow packet:

   ```bash
   python scripts/contextproof.py prepare-workflow /path/to/repo
   ```

   Add `--project-mode new_project` for a fresh repository or
   `--project-mode migration_project` for multi-agent context migration.

2. Read `.contextproof/workflow.md` and `.contextproof/optimizer-instructions.md`.
   These files identify the source context, selected route, template, candidate
   path, preservation requirements, and no-overwrite rule.

3. Read only the references needed for the selected route:

   - always read `references/context-optimizer.md`
   - read `references/classifier.md` only when route evidence is unclear
   - read the selected file under `references/templates/`
   - use `references/optimization-checklist.md` before recommending the result

4. Draft the candidate under `.contextproof/candidates/`. Preserve source
   filenames when possible, for example
   `.contextproof/candidates/AGENTS.contextproof.md`.

5. Never overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or
   other source context files unless the user explicitly approves after seeing
   the candidate and comparison report.

6. Review the original and candidate:

   ```bash
   python scripts/contextproof.py review-candidate /path/to/source/AGENTS.md /path/to/repo/.contextproof/candidates/AGENTS.contextproof.md
   ```

7. Report:

   - static score and critical/high findings
   - primary scenario and selected template
   - candidate path
   - score delta and token delta
   - preserved validation commands and project paths
   - regression flags and generated report paths

Treat regression flags as blockers until reviewed.

## Output Policy

- Write generated files under `.contextproof/` or a temporary directory.
- Do not claim real coding-agent performance improvement from static scores.
- Say when no validation command was found.
- Say when a candidate removed or negated a validation command, path anchor, or
  safety boundary.
- Keep the user's normal workflow simple; mention benchmark, gold, and calibration commands only for maintainers.

## Maintainer Commands

Use these only for ContextProof development:

```bash
python scripts/contextproof.py evaluate-gold SCENARIO_DIR CANDIDATE_PATH
python scripts/contextproof.py benchmark-optimizer examples/scenarios
python scripts/contextproof.py calibrate-scorer examples/calibration/cases.jsonl
python scripts/acceptance_v06.py
```

Gold references are benchmark fixtures only. Do not present them as automatic
answers for user repositories.

## References

- `references/context-optimizer.md`: candidate rules
- `references/templates/`: scenario templates
- `references/scoring-rubric.md`: scoring and calibration
- `references/benchmark-design.md`: benchmark and gold policy
