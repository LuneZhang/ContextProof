# Usage By Agent

ContextProof is skill-first. Install `skill/context-proof`, then ask the coding
agent to use it in natural language.

ContextProof is not a general Markdown optimizer. It only audits Markdown that
is loaded as coding-agent context.

Its core workflow is:

1. Prepare a workflow packet with `prepare-workflow`.
2. Read `.contextproof/workflow.md` and `.contextproof/optimizer-instructions.md`.
3. Draft optimized candidates under `.contextproof/candidates/`.
4. Review candidates with `review-candidate`.
5. Report adoption status, blockers, scenario, template, score delta, token
   delta, preserved requirements, and regression flags.

## Support Levels

| Agent surface | Recommended path |
| --- | --- |
| Codex | Native skill path |
| Claude Code | Native or project-local skill path |
| OpenCode | Native or project-local skill path |
| Cursor, Windsurf, Pi | Give the agent the skill folder path |
| Any shell-capable agent | Use the CLI fallback |

## Codex

Install:

```bash
mkdir -p ~/.codex/skills
cp -R skill/context-proof ~/.codex/skills/context-proof
```

Prompt:

```text
Use $context-proof to prepare the workflow, audit, and optimize this repository's agent context.
Read .contextproof/workflow.md and .contextproof/optimizer-instructions.md.
Write optimized drafts under .contextproof/candidates/.
Review each candidate with contextproof review-candidate.
Report adoption status, blockers, static score, primary scenario, selected template, score delta, token delta, preserved requirements, unresolved risks, regression flags, and generated files.
Do not overwrite existing context files.
```

After changing `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or other
agent context files, ask the agent to run:

```text
Use $context-proof to audit this repository's changed agent context and generate .contextproof/pr-comment.md.
```

## Claude Code

Project-local install:

```bash
mkdir -p .claude/skills
cp -R /path/to/ContextProof/skill/context-proof .claude/skills/context-proof
```

Prompt:

```text
Use the context-proof skill to audit and optimize this repository's coding-agent instructions.
Prepare the workflow packet first, then use .contextproof/workflow.md and .contextproof/optimizer-instructions.md.
Generate optimized candidates under .contextproof/candidates/ and review them with contextproof review-candidate.
Do not overwrite AGENTS.md, CLAUDE.md, or other existing context files.
```

## OpenCode

Project-local install:

```bash
mkdir -p .opencode/skills
cp -R /path/to/ContextProof/skill/context-proof .opencode/skills/context-proof
```

Prompt:

```text
Load the context-proof skill and audit this repository's agent context.
Prepare the workflow packet, draft optimized candidates under .contextproof/candidates/, review candidates with contextproof review-candidate, and summarize the generated .contextproof files.
```

## Cursor, Windsurf, Pi, And Other Agents

If the agent does not have native `SKILL.md` discovery, give it the skill path
directly:

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Prepare the workflow, audit, and optimize this repository's agent context.
Generate .contextproof/workflow.md, .contextproof/optimizer-instructions.md,
optimized drafts under .contextproof/candidates/, and candidate review reports.
Do not overwrite existing context files.
```

If the agent cannot run a skill folder directly, install the CLI fallback:

```bash
python -m pip install -e /path/to/ContextProof
contextproof prepare-workflow .
```

For PR-style local review:

```bash
contextproof audit . --pr-comment --changed-against origin/main...HEAD
```

To compare an optimized candidate:

```bash
contextproof review-candidate AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

Maintainer-only fixture evaluation:

```bash
contextproof evaluate-gold examples/scenarios/existing-project-overbroad \
  examples/scenarios/existing-project-overbroad/gold/AGENTS.gold.md
```

Maintainer-only prompt variant benchmark:

```bash
contextproof benchmark-optimizer examples/scenarios \
  --prompt-variant baseline \
  --jsonl-out .contextproof/optimizer-runs.jsonl \
  --md-out .contextproof/optimizer-summary.md
```

Maintainer-only scorer calibration:

```bash
contextproof calibrate-scorer examples/calibration/cases.jsonl \
  --json-out .contextproof/scorer-calibration.json \
  --md-out .contextproof/scorer-calibration.md
```

To run the full maintainer acceptance flow:

```bash
python scripts/acceptance_v06.py
```

To compare against a saved report:

```bash
contextproof audit . --baseline .contextproof/report.main.json --pr-comment
```

## Project Mode

Default to `existing_project`. For fresh repositories, ask the agent to use
`--project-mode new_project`. For migrations between agents or stacks, use
`--project-mode migration_project` for reporting and benchmark labeling.

## What The Agent Should Report

Ask for:

- adoption status
- candidate blockers
- static context score
- primary scenario
- selected optimizer template
- candidate score delta
- estimated token delta
- confidence state
- critical/high findings
- preserved validation commands and project paths
- regression flags
- evidence and issue categories
- generated file paths

Avoid asking the agent to claim real performance improvement unless benchmark
evidence exists.
