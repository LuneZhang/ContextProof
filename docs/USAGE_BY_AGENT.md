# Usage By Agent

ContextProof is skill-first. Install `skill/context-proof`, then ask the coding
agent to use it in natural language.

## Codex

Install:

```bash
mkdir -p ~/.codex/skills
cp -R skill/context-proof ~/.codex/skills/context-proof
```

Prompt:

```text
Use $context-proof to audit this repository's agent context.
Report the static score, confidence state, critical/high findings, evidence, and generated files.
Do not overwrite existing context files.
```

## Claude Code

Project-local install:

```bash
mkdir -p .claude/skills
cp -R /path/to/ContextProof/skill/context-proof .claude/skills/context-proof
```

Prompt:

```text
Use the context-proof skill to audit this repository's coding-agent instructions.
Generate the local report and PR comment.
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
Summarize the findings and show the generated .contextproof files.
```

## Cursor, Windsurf, Pi, And Other Agents

If the agent does not have native `SKILL.md` discovery, give it the skill path
directly:

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit this repository's agent context. Generate .contextproof/report.md,
.contextproof/pr-comment.md. Do not overwrite existing context files.
```

If the agent cannot run a skill folder directly, install the CLI fallback:

```bash
python -m pip install -e /path/to/ContextProof
contextproof audit . --pr-comment
```

## What The Agent Should Report

Ask for:

- static context score
- confidence state
- critical/high findings
- evidence and issue categories
- generated file paths

Avoid asking the agent to claim real performance improvement unless benchmark
evidence exists.
