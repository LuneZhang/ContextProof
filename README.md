# ContextProof

Audit and optimize the Markdown instructions your coding agent reads before it
edits code.

[Chinese README](README.zh-CN.md)

ContextProof is a portable skill for agent-facing context files such as
`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, MCP notes, and saved
`/init` briefs. It is not a general Markdown linter.

## Copy Into Your Coding Agent

```text
Install ContextProof from https://github.com/LuneZhang/ContextProof, then use
the context-proof skill to audit and optimize this repository's agent context.
Write candidates under .contextproof/candidates/, compare them with the
originals, and do not overwrite AGENTS.md, CLAUDE.md, .cursor/rules, SKILL.md,
or other context files.
```

After the skill is installed:

```text
Use $context-proof to prepare the workflow, audit, and optimize this repository's agent context.
```

Expected local output:

```text
.contextproof/report.md
.contextproof/pr-comment.md
.contextproof/context-discovery.md
.contextproof/context-classification.md
.contextproof/optimizer-instructions.md
.contextproof/workflow.md
.contextproof/candidates/AGENTS.contextproof.md
.contextproof/candidate-review.md
```

## Install

Python 3.11 or newer is required for the bundled deterministic runner.

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

Shortcut installer on macOS, Linux, or WSL:

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
`project-agents`, `project-claude`, and `project-opencode`. The installers only
copy `skill/context-proof`; they do not modify your existing agent context
files.

## What It Does

ContextProof helps a coding agent improve persistent context without replacing
the source file automatically:

1. `prepare-workflow`: discovers agent context, audits it, classifies the
   scenario, routes the optimizer, and writes `.contextproof/workflow.md`.
2. The coding agent drafts a candidate under `.contextproof/candidates/`.
3. `review-candidate`: checks blockers, score delta, token delta,
   preservation, and regressions before the user decides whether to adopt.

Scenario routes:

- `new-project-init-summary`
- `existing-project-agent-rules`
- `multi-agent-context-migration`
- `workflow-sop-context`
- `safety-sensitive-context`
- `token-heavy-context`

## Use Manually

The skill is the primary product. The CLI is the deterministic runner behind
the skill and a fallback for shell-capable agents.

```bash
python -m pip install -e .
contextproof prepare-workflow .
contextproof review-candidate AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

Lower-level commands remain available when an agent needs them:

```bash
contextproof discover-context .
contextproof audit . --pr-comment
contextproof classify-context AGENTS.md
contextproof route-optimizer AGENTS.md
contextproof compare-context AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

Fresh repositories:

```bash
contextproof prepare-workflow . --project-mode new_project
```

Migration between agent surfaces:

```bash
contextproof prepare-workflow . --project-mode migration_project
```

## What It Audits

| Audited | Not audited |
| --- | --- |
| Persistent instructions a coding agent actually reads | Ordinary README files |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Design docs and product docs |
| `.cursor/rules/*.{md,mdc,txt}` | One-off chat prompts |
| `.github/copilot-instructions.md` | Markdown never injected into agent context |
| `SKILL.md`, MCP notes, saved `/init` briefs | Native `/init` output unless saved as context |

ContextProof does not run Codex, Claude Code, OpenCode, Cursor, Gemini,
Copilot, or Pi. It audits local files and writes local reports.

## Capability Boundaries

ContextProof is deliberately small:

- It detects and evaluates context problems; it does not run a hosted rewrite
  service.
- It guides the active coding agent to draft candidates; it does not overwrite
  source context files.
- It uses deterministic checks; it does not use an LLM judge.
- Gold references, scorer calibration, and acceptance tests are maintainer
  tools, not the normal user workflow.

See [Capability Boundaries](docs/CAPABILITY_BOUNDARIES.md) for the detailed
boundary and size-control plan.

## Maintainer Workflow

Built-in fixtures and calibration are used to improve ContextProof itself.

```bash
contextproof evaluate-gold examples/scenarios/existing-project-overbroad \
  examples/scenarios/existing-project-overbroad/gold/AGENTS.gold.md

contextproof benchmark-optimizer examples/scenarios \
  --prompt-variant baseline \
  --jsonl-out .contextproof/optimizer-runs.jsonl \
  --md-out .contextproof/optimizer-summary.md

contextproof calibrate-scorer examples/calibration/cases.jsonl \
  --json-out .contextproof/scorer-calibration.json \
  --md-out .contextproof/scorer-calibration.md
```

Run the full local acceptance flow:

```bash
python scripts/acceptance_v06.py
```

`make acceptance` is also available on systems with `make`.

## Repository Layout

```text
contextproof/                 Python package and CLI runner
skill/context-proof/          Portable agent skill
schemas/                      JSON schemas
examples/                     Scenario fixtures, gold references, calibration cases
docs/                         Usage, roadmap, capability boundaries
tests/                        Unit tests
```

## References

- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [OpenCode Agent Skills](https://opencode.ai/docs/skills/)

## License

MIT
