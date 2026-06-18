# ContextProof

审查并优化 coding agent 在改代码前会读取的 Markdown 指令。

[English README](README.md)

ContextProof 是一个可安装到 coding agent 中的便携 skill，面向
`AGENTS.md`、`CLAUDE.md`、`.cursor/rules`、`SKILL.md`、MCP notes、已保存的
`/init` 仓库说明等 agent-facing context。它不是通用 Markdown linter。

## 复制给你的 Coding Agent

```text
从 https://github.com/LuneZhang/ContextProof 安装 ContextProof，然后使用
context-proof skill 审查并优化当前仓库的 agent context。把候选版本写到
.contextproof/candidates/，和原文对比，不要覆盖 AGENTS.md、CLAUDE.md、
.cursor/rules、SKILL.md 或其他 context 文件。
```

skill 安装后可以直接说：

```text
Use $context-proof to audit and optimize this repository's agent context.
```

典型本地产物：

```text
.contextproof/report.md
.contextproof/pr-comment.md
.contextproof/context-classification.md
.contextproof/optimizer-instructions.md
.contextproof/candidates/AGENTS.contextproof.md
.contextproof/candidate-report.md
```

## 安装

内置 deterministic runner 需要 Python 3.11 或更新版本。

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

macOS、Linux、WSL：

```bash
./scripts/install-contextproof-skill.sh codex
./scripts/install-contextproof-skill.sh claude
./scripts/install-contextproof-skill.sh opencode
./scripts/install-contextproof-skill.sh project-agents
```

Windows PowerShell：

```powershell
.\scripts\install-contextproof-skill.ps1 codex
.\scripts\install-contextproof-skill.ps1 claude
.\scripts\install-contextproof-skill.ps1 opencode
.\scripts\install-contextproof-skill.ps1 project-agents
```

支持的安装范围：`agents`、`codex`、`claude`、`opencode`、`project-agents`、
`project-claude`、`project-opencode`。安装脚本只复制 `skill/context-proof`，
不会修改你的现有 agent context 文件。

## 它做什么

ContextProof 帮助 coding agent 优化持久化上下文，但不会自动替换源文件：

1. `audit`：发现模糊、不安全、冲突、过大、不可验收的指令。
2. `classify-context`：判断 context 使用场景。
3. `route-optimizer`：选择对应优化模板。
4. coding agent 在 `.contextproof/candidates/` 下写候选版本。
5. `compare-context`：检查分数变化、token 变化、保留项和回归风险。

支持的场景：

- `new-project-init-summary`
- `existing-project-agent-rules`
- `multi-agent-context-migration`
- `workflow-sop-context`
- `safety-sensitive-context`
- `token-heavy-context`

## 手动使用

skill 是主要产品形态。CLI 是 skill 背后的 deterministic runner，也是无法直接加载
skill 时的 fallback。

```bash
python -m pip install -e .
contextproof audit . --pr-comment
contextproof classify-context AGENTS.md
contextproof route-optimizer AGENTS.md
contextproof compare-context AGENTS.md .contextproof/candidates/AGENTS.contextproof.md
```

新项目：

```bash
contextproof audit . --project-mode new_project --pr-comment
contextproof route-optimizer AGENTS.md --project-mode new_project
```

多 agent context 迁移：

```bash
contextproof audit . --project-mode migration_project --pr-comment
```

## 审查对象

| 审查 | 不审查 |
| --- | --- |
| coding agent 实际读取的持久化指令 | 普通 README |
| `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` | 设计文档和产品文档 |
| `.cursor/rules/*.{md,mdc,txt}` | 一次性聊天提示词 |
| `.github/copilot-instructions.md` | 不会注入 agent context 的 Markdown |
| `SKILL.md`、MCP notes、已保存 `/init` 说明 | 未保存成 context 文件的原始 `/init` 输出 |

ContextProof 不会自动运行 Codex、Claude Code、OpenCode、Cursor、Gemini、
Copilot 或 Pi。它只审查本地文件并写本地报告。

## 能力边界

ContextProof 有意保持小而专注：

- 它发现并评估 context 问题，不提供托管改写服务。
- 它指导当前 coding agent 写候选版本，不自动覆盖源文件。
- 它使用 deterministic checks，不使用 LLM judge。
- Gold reference、scorer calibration、acceptance test 是维护者工具，不是普通用户主流程。

详见 [能力边界](docs/CAPABILITY_BOUNDARIES.md)。

## 维护者工作流

内置 fixtures 和 calibration 用于改进 ContextProof 自身。

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

完整本地验收：

```bash
python scripts/acceptance_v05.py
```

有 `make` 的环境也可以运行 `make acceptance`。

## 仓库结构

```text
contextproof/                 Python package 和 CLI runner
skill/context-proof/          便携 agent skill
schemas/                      JSON schemas
examples/                     场景 fixtures、gold references、calibration cases
docs/                         使用说明、路线图、能力边界
tests/                        单元测试
```

## 许可

MIT
