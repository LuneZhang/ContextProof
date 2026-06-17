# ContextProof

审计 coding agent 在修改代码前读取的指令。

[English README](README.md)

ContextProof 是一个开源 agent skill，用于检查仓库级 coding-agent context：
`AGENTS.md`、`CLAUDE.md`、`.cursor/rules`、`SKILL.md`、MCP notes 以及类似的
指令文件。安装 skill 后，用户可以在自己的 coding agent 里用自然语言调用它。

## 主要用法

安装 skill 后，对你的 coding agent 说：

```text
Use the context-proof skill to audit this repository's agent context.
Generate the report and local PR comment.
Do not overwrite existing AGENTS.md, CLAUDE.md, or other context files.
```

Codex 中可以直接说：

```text
Use $context-proof to audit this repository's agent context.
```

ContextProof 会在 `.contextproof/` 下生成本地产物：

- `report.json`：机器可读审计结果
- `report.md`：人类可读审计报告
- `pr-comment.md`：可复制到 PR 的本地评论文本
- `context.min.md`：显式请求时生成的通用起始候选
- `minimize-rationale.md`：可选候选文件生成说明

更多 agent 的调用方式见 [Usage By Agent](docs/USAGE_BY_AGENT.md)。

## 为什么还有 CLI

ContextProof 是 skill-first。CLI 是 skill 背后的确定性执行器。

这样 agent 不需要只靠主观判断来评价 context，而是可以调用一个可复现的本地 runner。
同一个 runner 也可以用于 CI、本地调试和 demo：

```bash
contextproof audit . --pr-comment
```

CLI 不是主要用户体验。主要体验是：安装 skill，然后让 coding agent 使用它。

## 当前 V0.1.1 功能

- 可移植的 `context-proof` skill，包含 `SKILL.md`、脚本、参考文档和资源。
- 对 agent context 文件进行确定性静态审计。
- 六个维度的静态评分：可发现性、可执行性、精简度、一致性、安全性、工作流匹配度。
- 检测模糊规则、过度宽泛的探索规则、危险 shell 文本、类似 prompt injection 的语言、
  重复规则、矛盾规则、缺少验证命令和过大的 context。
- 在 `.contextproof/` 下生成本地报告。
- 生成本地 PR comment markdown。
- 显式请求时生成通用 `AGENTS.md` 起始候选，不作为项目级自动修复。
- 汇总已记录的 benchmark JSONL。
- 为报告和 benchmark run 提供 JSON schema。
- 可选 CLI，用于 CI 和手动 fallback。

## V0.1 边界

这个版本刻意保持窄边界：

- 不自动运行 Codex、Claude Code、OpenCode、Cursor、Gemini、Copilot 或 Pi。
- 不调用 GitHub API。
- 不声称静态分数可以证明真实 agent 性能提升。
- 不自动覆盖现有 context 文件。

行为效果声明需要真实记录的 benchmark runs。V0.1 可以汇总这些 run 记录，但不会自动采集。

## 安装

内置确定性 runner 需要 Python 3.11 或更新版本。

克隆仓库：

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

Windows PowerShell：

```powershell
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
```

### 安装 Skill

通用全局位置：

macOS、Linux、WSL：

```bash
mkdir -p ~/.agents/skills
cp -R skill/context-proof ~/.agents/skills/context-proof
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force .\skill\context-proof "$HOME\.agents\skills\context-proof"
```

快捷脚本：

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

macOS、Linux、WSL：

```bash
mkdir -p ~/.codex/skills
cp -R skill/context-proof ~/.codex/skills/context-proof
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force .\skill\context-proof "$HOME\.codex\skills\context-proof"
```

使用：

```text
Use $context-proof to audit this repository's agent context.
```

### Claude Code

项目内安装：

```bash
mkdir -p .claude/skills
cp -R /path/to/ContextProof/skill/context-proof .claude/skills/context-proof
```

用户全局安装：

```bash
mkdir -p ~/.claude/skills
cp -R /path/to/ContextProof/skill/context-proof ~/.claude/skills/context-proof
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force C:\path\to\ContextProof\skill\context-proof "$HOME\.claude\skills\context-proof"
```

使用：

```text
Use the context-proof skill to audit this repository's coding-agent instructions.
```

### OpenCode

项目内安装：

```bash
mkdir -p .opencode/skills
cp -R /path/to/ContextProof/skill/context-proof .opencode/skills/context-proof
```

全局安装：

```bash
mkdir -p ~/.config/opencode/skills
cp -R /path/to/ContextProof/skill/context-proof ~/.config/opencode/skills/context-proof
```

使用：

```text
Load the context-proof skill and audit this repository's agent context.
```

### 其他 Coding Agents

对于 Cursor、Windsurf、Pi coding agent 或不支持原生 `SKILL.md` 发现的 agent，可以直接给出 skill 路径：

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit this repository's agent context, generate `.contextproof/report.md`,
and generate `.contextproof/pr-comment.md`. Do not overwrite existing context files.
```

## 可选 CLI 安装

如果需要 shell 命令、CI job，或 agent 无法直接加载 skill，可以安装 CLI：

macOS、Linux、WSL：

```bash
python3 -m pip install -e .
contextproof audit /path/to/repo --pr-comment
```

Windows PowerShell：

```powershell
py -m pip install -e .
contextproof audit C:\path\to\repo --pr-comment
```

不安装也可以运行：

```bash
python -m contextproof.cli audit /path/to/repo --pr-comment
```

## Demo

审计一个故意写坏的 `AGENTS.md` 示例：

```bash
python -m contextproof.cli audit examples/bad-agent-context --pr-comment
```

报告会标出模糊规则、过度宽泛探索、危险 shell 文本、矛盾指令和缺失验证命令。

## CLI 命令

```bash
contextproof quickstart .
contextproof audit . --pr-comment
contextproof minimize . --output AGENTS.min.md
contextproof explain .contextproof/report.json
contextproof summarize-runs examples/benchmark-runs.jsonl
```

严格 CI gate 是可选项：

```bash
contextproof audit . --fail-under 70 --pr-comment
```

默认 GitHub workflow 只上传 artifact，不因为静态分数失败而阻断 PR，除非显式添加 `--fail-under`。

## Benchmark 数据

ContextProof 区分静态 hygiene 和行为证据。静态分数不代表 agent 一定表现更好。
行为结论需要成对记录的 run 数据，例如：

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

汇总本地 JSONL：

```bash
contextproof summarize-runs examples/benchmark-runs.jsonl \
  --md-out .contextproof/benchmark-summary.md
```

## 仓库结构

```text
contextproof/                 Python package 和 CLI 实现
skill/context-proof/          可移植 agent skill
schemas/                      报告与 benchmark run 的 JSON schema
examples/                     示例数据与 demo fixture
integrations/                 不同 agent 的可选命令模板
tests/                        单元测试
```

## License

MIT
