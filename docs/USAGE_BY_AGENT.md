# Usage By Agent

ContextProof is skill-first. Install `skill/context-proof`, then ask the coding
agent to use it in natural language.

ContextProof is not a general Markdown optimizer. It only audits Markdown that
is loaded as coding-agent context.

Its core workflow is:

1. Audit agent-facing context.
2. Draft optimized candidates under `.contextproof/candidates/`.
3. Compare candidates against the original context.
4. Report score delta, token delta, preserved requirements, unresolved risks,
   and regression flags.

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
Use $context-proof to audit and optimize this repository's agent context.
Write optimized drafts under .contextproof/candidates/.
Compare each candidate against its original context.
Report static score, score delta, token delta, preserved requirements, unresolved risks, regression flags, and generated files.
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
Generate optimized candidates under .contextproof/candidates/ and compare them against the originals.
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
Draft optimized candidates under .contextproof/candidates/, compare them against the originals, and summarize the generated .contextproof files.
```

## Cursor, Windsurf, Pi, And Other Agents

If the agent does not have native `SKILL.md` discovery, give it the skill path
directly:

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit and optimize this repository's agent context. Generate .contextproof/report.md,
.contextproof/pr-comment.md, optimized drafts under .contextproof/candidates/,
and candidate comparison reports. Do not overwrite existing context files.
```

If the agent cannot run a skill folder directly, install the CLI fallback:

```bash
python -m pip install -e /path/to/ContextProof
contextproof audit . --pr-comment
```

For PR-style local review:

```bash
contextproof audit . --pr-comment --changed-against origin/main...HEAD
```

To compare an optimized candidate:

```bash
contextproof compare-context AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

To evaluate optimizer prompt variants against prepared scenarios:

```bash
contextproof benchmark-optimizer examples/scenarios \
  --prompt-variant baseline \
  --jsonl-out .contextproof/optimizer-runs.jsonl \
  --md-out .contextproof/optimizer-summary.md
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

- static context score
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
