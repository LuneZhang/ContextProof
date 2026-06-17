# ContextProof

Audit the instructions your coding agent reads before it edits code.

[中文 README](README.zh-CN.md)

ContextProof is an open-source agent skill for checking repository-level coding
agent context: `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, MCP notes,
and similar instruction files. Install the skill in your coding agent, then ask
the agent to audit the current repository in natural language.

## Primary Use

After installing the skill, ask your coding agent:

```text
Use the context-proof skill to audit this repository's agent context.
Generate the report and local PR comment.
Do not overwrite existing AGENTS.md, CLAUDE.md, or other context files.
```

For Codex, the direct form is:

```text
Use $context-proof to audit this repository's agent context.
```

ContextProof writes local artifacts under `.contextproof/`:

- `report.json`: machine-readable audit result
- `report.md`: human-readable audit report
- `pr-comment.md`: local PR comment text
- `context.min.md`: optional generic starter candidate when explicitly requested
- `minimize-rationale.md`: why the optional candidate was generated

See [Usage By Agent](docs/USAGE_BY_AGENT.md) for Codex, Claude Code, OpenCode,
Cursor, Windsurf, Pi, and generic-agent prompts.

## Why There Is A CLI

ContextProof is skill-first. The CLI exists as the deterministic runner that
the skill can call.

That gives the agent a reliable execution path instead of asking it to judge
agent context only by intuition. The same runner also makes CI, local debugging,
and reproducible examples possible:

```bash
contextproof audit . --pr-comment
```

The CLI is not the primary user experience. The primary experience is: install
the skill, then ask the coding agent to use it.

## Current V0.1.1 Features

- Portable `context-proof` skill with `SKILL.md`, scripts, references, and assets.
- Deterministic static audit for agent context files.
- Six-dimension static score: discoverability, actionability, minimality,
  consistency, safety, and workflow fit.
- Detection for vague rules, over-broad exploration rules, risky shell text,
  prompt-injection-like language, duplicated rules, contradictions, missing
  validation commands, and oversized context.
- Local report generation under `.contextproof/`.
- Local PR-comment markdown generation.
- Optional generic `AGENTS.md` starter candidate when explicitly requested.
- Benchmark JSONL summary for recorded agent runs.
- JSON schemas for report and benchmark run data.
- Optional CLI entry point for CI and manual fallback.

## Try The Demo

Audit an intentionally flawed `AGENTS.md` fixture:

```bash
python -m contextproof.cli audit examples/bad-agent-context --pr-comment
```

The report should flag vague rules, over-broad exploration, risky shell text,
contradictory instructions, and missing validation commands.

## V0.1 Boundary

This release is intentionally narrow:

- It does not run Codex, Claude Code, OpenCode, Cursor, Gemini, Copilot, or Pi.
- It does not call the GitHub API.
- It does not claim a static score proves real agent performance improvement.
- It does not automatically overwrite existing context files.

Behavioral claims require recorded benchmark runs. V0.1 can summarize those run
records, but it does not collect them automatically.

## Install

Python 3.11 or newer is required for the bundled deterministic runner.

Clone the repository:

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

Windows PowerShell:

```powershell
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

### Install The Skill

Agent-portable global location:

macOS, Linux, WSL:

```bash
mkdir -p ~/.agents/skills
cp -R skill/context-proof ~/.agents/skills/context-proof
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force .\skill\context-proof "$HOME\.agents\skills\context-proof"
```

Shortcut scripts:

```bash
sh scripts/install-contextproof-skill.sh agents
sh scripts/install-contextproof-skill.sh codex
sh scripts/install-contextproof-skill.sh claude
sh scripts/install-contextproof-skill.sh opencode
```

```powershell
.\scripts\install-contextproof-skill.ps1 -Scope agents
.\scripts\install-contextproof-skill.ps1 -Scope codex
.\scripts\install-contextproof-skill.ps1 -Scope claude
.\scripts\install-contextproof-skill.ps1 -Scope opencode
```

### Codex

macOS, Linux, WSL:

```bash
mkdir -p ~/.codex/skills
cp -R skill/context-proof ~/.codex/skills/context-proof
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force .\skill\context-proof "$HOME\.codex\skills\context-proof"
```

Use:

```text
Use $context-proof to audit this repository's agent context.
```

### Claude Code

Project-local install:

```bash
mkdir -p .claude/skills
cp -R /path/to/ContextProof/skill/context-proof .claude/skills/context-proof
```

User/global install:

```bash
mkdir -p ~/.claude/skills
cp -R /path/to/ContextProof/skill/context-proof ~/.claude/skills/context-proof
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force C:\path\to\ContextProof\skill\context-proof "$HOME\.claude\skills\context-proof"
```

Use:

```text
Use the context-proof skill to audit this repository's coding-agent instructions.
```

### OpenCode

Project-local install:

```bash
mkdir -p .opencode/skills
cp -R /path/to/ContextProof/skill/context-proof .opencode/skills/context-proof
```

Global install:

```bash
mkdir -p ~/.config/opencode/skills
cp -R /path/to/ContextProof/skill/context-proof ~/.config/opencode/skills/context-proof
```

Use:

```text
Load the context-proof skill and audit this repository's agent context.
```

### Other Coding Agents

For Pi coding agent and agents without native `SKILL.md` discovery, ask the
agent to use the skill folder directly:

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit this repository's agent context, generate `.contextproof/report.md`,
and generate `.contextproof/pr-comment.md`. Do not overwrite existing context files.
```

## Optional CLI Install

Install the CLI when you want a shell command, CI job, or fallback path for an
agent that can run Python but cannot load skills directly.

macOS, Linux, WSL:

```bash
python3 -m pip install -e .
contextproof audit /path/to/repo --pr-comment
```

Windows PowerShell:

```powershell
py -m pip install -e .
contextproof audit C:\path\to\repo --pr-comment
```

Run without installing:

```bash
python -m contextproof.cli audit /path/to/repo --pr-comment
```

## CLI Commands

```bash
contextproof quickstart .
contextproof audit . --pr-comment
contextproof minimize . --output AGENTS.min.md
contextproof explain .contextproof/report.json
contextproof summarize-runs examples/benchmark-runs.jsonl
```

Strict CI gating is opt-in:

```bash
contextproof audit . --fail-under 70 --pr-comment
```

The included GitHub workflow writes artifacts by default; it does not fail PRs
on static score unless `--fail-under` is added.

## Benchmark Data

ContextProof separates static hygiene from behavioral evidence. A static score
does not claim agents will perform better. Behavioral claims require recorded
paired run data with fields such as:

- `task_id`
- `variant`
- `paired_group_id`
- `agent`
- `model`
- `repo_snapshot`
- `success`
- `tests_passed`
- `tokens_input`
- `tokens_output`
- `duration_seconds`
- `files_read`
- `files_changed`
- `commands_run`
- `instruction_violations`

Summarize local JSONL runs:

```bash
contextproof summarize-runs examples/benchmark-runs.jsonl \
  --md-out .contextproof/benchmark-summary.md
```

## Repository Layout

```text
contextproof/                 Python package and CLI implementation
skill/context-proof/          Portable agent skill
schemas/                      JSON schemas for reports and benchmark runs
examples/                     Example benchmark JSONL
integrations/                 Optional command templates for specific agents
tests/                        Unit tests
```

## References

- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [OpenCode Agent Skills](https://opencode.ai/docs/skills/)

## License

MIT
