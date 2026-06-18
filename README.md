# ContextProof

Audit and optimize the instructions your coding agent reads before it edits
code.

[中文 README](README.zh-CN.md)

ContextProof checks agent-facing Markdown such as `AGENTS.md`, `CLAUDE.md`,
`.cursor/rules`, `SKILL.md`, MCP notes, and persisted `/init` briefs before
they are injected into a coding agent's prompt context.

ContextProof is not a general Markdown optimizer or linter. It only audits
Markdown that is loaded as coding-agent context.

It looks for instructions that are vague, contradictory, unsafe, too broad,
hard to validate, or wasteful for the model to carry on every task. It can also
guide your coding agent to draft a safer, shorter candidate context file and
then compare that candidate against the original.

## Copy Into Your Agent

```text
Install ContextProof from https://github.com/LuneZhang/ContextProof.
Use the context-proof skill to audit and optimize this repository's agent context.
Write optimized drafts under .contextproof/candidates/.
Compare the original and candidate context.
Do not overwrite AGENTS.md, CLAUDE.md, .cursor/rules, SKILL.md, or other context files.
```

Codex direct form after installing the skill:

```text
Use $context-proof to audit and optimize this repository's agent context.
Write optimized drafts under .contextproof/candidates/ and compare them against the originals.
```

Expected output:

```text
Static context score: 62 / 100
Benchmark evidence: not_provided

Findings:
- [critical] risky-shell: unsafe shell pattern in AGENTS.md
- [high] overbroad-context: asks the agent to read the entire repository
- [high] missing-test-command: no validation command discovered

Generated:
- .contextproof/report.md
- .contextproof/pr-comment.md
- .contextproof/candidates/AGENTS.contextproof.md
- .contextproof/candidate-report.md
```

## Try The Demo

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
python -m contextproof.cli audit examples/bad-agent-context --pr-comment
```

The demo flags vague rules, over-broad exploration, risky shell text,
contradictory instructions, and missing validation commands.

For a more realistic accumulated team-context example:

```bash
python -m contextproof.cli audit examples/team-agent-context --pr-comment
```

## After Editing Agent Context

Run ContextProof after changing `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`.cursor/rules`, `SKILL.md`, MCP notes, or other persisted agent instructions:

```bash
contextproof audit . --pr-comment
```

To compare an optimized candidate against the original context:

```bash
contextproof compare-context AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

The candidate report flags score delta, estimated token delta, resolved
findings, introduced findings, removed validation commands, and preservation
risks.

If the change is part of a PR, use `.contextproof/pr-comment.md` as the local
review summary for the context change.

To compare the current branch against a base ref in a PR-style workflow:

```bash
contextproof audit . --pr-comment --changed-against origin/main...HEAD
```

## What It Audits

| Audited | Not Audited |
| --- | --- |
| Persistent instructions a coding agent actually reads | General project documentation |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Ordinary README or design docs |
| `.cursor/rules/*.{md,mdc,txt}` | Markdown that is never injected into agent context |
| `.github/copilot-instructions.md` | One-off chat prompts not saved as context |
| `SKILL.md`, MCP notes, agent notes | Native `/init` output unless saved as a context file |

ContextProof does not run Codex, Claude Code, OpenCode, Cursor, Gemini,
Copilot, or Pi. It audits local context files and writes local reports.

## Core Output

ContextProof writes local artifacts under `.contextproof/`:

- `report.json`: machine-readable audit result
- `report.md`: human-readable audit report
- `pr-comment.md`: local PR comment text

The static audit reports:

- six-dimension score: discoverability, actionability, minimality, consistency,
  safety, and workflow fit
- findings for vague rules, over-broad exploration, risky shell text,
  prompt-injection-like language, duplicate rules, contradictions, missing
  validation commands, and oversized context
- recommendations for what a human or agent should inspect next

## Install The Skill

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

Shortcut installer:

```bash
./scripts/install-contextproof-skill.sh codex
./scripts/install-contextproof-skill.sh claude
./scripts/install-contextproof-skill.sh opencode
./scripts/install-contextproof-skill.sh project-agents
```

Windows PowerShell:

```powershell
.\scripts\install-contextproof-skill.ps1 codex
.\scripts\install-contextproof-skill.ps1 claude
.\scripts\install-contextproof-skill.ps1 opencode
.\scripts\install-contextproof-skill.ps1 project-agents
```

Supported installer scopes: `agents`, `codex`, `claude`, `opencode`,
`project-agents`, `project-claude`, and `project-opencode`. The installers
only copy the `skill/context-proof` folder; they do not modify your agent
context files.

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

| Agent surface | Recommended path |
| --- | --- |
| Codex | Native skill path |
| Claude Code | Native or project-local skill path |
| OpenCode | Native or project-local skill path |
| Cursor, Windsurf, Pi | Give the agent the skill folder path |
| Any shell-capable agent | Use the CLI fallback |

Prompt fallback:

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit this repository's agent context. Generate .contextproof/report.md and
.contextproof/pr-comment.md. Do not overwrite existing context files.
```

See [Usage By Agent](docs/USAGE_BY_AGENT.md) for more prompts.

## Optional CLI

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

Compare a source context file and an optimized candidate:

```bash
contextproof compare-context AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

Record optimizer prompt-variant results across the included scenario fixtures:

```bash
contextproof benchmark-optimizer examples/scenarios \
  --prompt-variant baseline \
  --jsonl-out .contextproof/optimizer-runs.jsonl \
  --md-out .contextproof/optimizer-summary.md
```

## Project Modes

| Mode | Use When | V0.2 Behavior |
| --- | --- | --- |
| `existing_project` | The repository already has code and workflows | Default audit mode |
| `new_project` | You are bootstrapping a fresh repository | Missing context is reported with lower severity |
| `migration_project` | You are migrating rules between agents or stacks | Accepted for reporting and benchmark labeling |

Example:

```bash
python -m contextproof.cli audit . --project-mode new_project --pr-comment
```

## Advanced

### Benchmark Evidence

ContextProof separates static hygiene from behavioral evidence. A static score
does not prove agents will perform better. Behavioral claims require recorded
paired run data.

Canonical variants:

- `none`: no repository context file injected
- `current`: the repository's current context files
- `native-init`: a tool's default generated context from an `/init`-style flow
- `contextproof-reviewed`: context after a human or agent reviews
  ContextProof findings and makes explicit changes

Summarize local JSONL runs:

```bash
contextproof summarize-runs examples/benchmark-runs.jsonl \
  --md-out .contextproof/benchmark-summary.md
```

Merge recorded runs into an audit report:

```bash
contextproof audit . --runs examples/benchmark-runs.jsonl --pr-comment
```

### Starter Scaffold

`contextproof minimize` writes a generic starter scaffold only when explicitly
requested. It is not a project-specific rewrite and does not replace existing
context files.

```bash
contextproof minimize . --output AGENTS.starter.md
```

### CI

Strict CI gating is opt-in:

```bash
contextproof audit . --fail-under 70 --pr-comment
```

The included GitHub workflow writes artifacts by default; it does not fail PRs
on static score unless `--fail-under` is added. The workflow is scoped to
agent-context file changes.

### Baseline Reports

Create or refresh a baseline report from the branch you trust, usually `main`:

```bash
contextproof audit . --json-out .contextproof/report.main.json
```

Compare the current audit against a previously saved report:

```bash
contextproof audit . --baseline .contextproof/report.main.json --pr-comment
```

The PR comment will include score delta, new findings, and resolved findings.

## Repository Layout

```text
contextproof/                 Python package and CLI implementation
skill/context-proof/          Portable agent skill
schemas/                      JSON schemas for reports and benchmark runs
examples/                     Example benchmark JSONL and demo fixture
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
