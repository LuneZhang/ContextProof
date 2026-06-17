# ContextProof

审计 coding agent 在修改代码前读取的指令。

[English README](README.md)

ContextProof 检查会被 coding agent 读取并拼接进提示词上下文的 Markdown：
`AGENTS.md`、`CLAUDE.md`、`.cursor/rules`、`SKILL.md`、MCP notes，以及被持久化保存的
`/init` 仓库说明。

ContextProof 不是通用 Markdown 优化器或 linter。它只审计会被加载为 coding-agent context 的 Markdown。

它专门发现那些会让 agent 浪费 token、误解任务、缺少验收方式、规则互相矛盾或存在安全风险的长期指令。

## 复制给你的 Agent

```text
Install ContextProof from https://github.com/LuneZhang/ContextProof.
Use the context-proof skill to audit this repository's agent context.
Generate .contextproof/report.md and .contextproof/pr-comment.md.
Do not overwrite AGENTS.md, CLAUDE.md, .cursor/rules, SKILL.md, or other context files.
```

Codex 安装 skill 后可以直接说：

```text
Use $context-proof to audit this repository's agent context.
```

预期输出示例：

```text
Static context score: 62 / 100
Benchmark evidence: not_provided

Findings:
- [critical] risky-shell: AGENTS.md 中存在危险 shell 模式
- [high] overbroad-context: 要求 agent 读取整个仓库
- [high] missing-test-command: 没有发现验收命令

Generated:
- .contextproof/report.md
- .contextproof/pr-comment.md
```

## 试运行 Demo

```bash
git clone https://github.com/LuneZhang/ContextProof.git
cd ContextProof
python -m contextproof.cli audit examples/bad-agent-context --pr-comment
```

demo 会标出模糊规则、过度宽泛探索、危险 shell 文本、矛盾指令和缺失验证命令。

更接近真实团队规则债的示例：

```bash
python -m contextproof.cli audit examples/team-agent-context --pr-comment
```

## 修改 Agent Context 后

修改 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.cursor/rules`、`SKILL.md`、MCP notes
或其他持久化 agent 指令后，运行：

```bash
contextproof audit . --pr-comment
```

如果这些文件变更属于 PR，可以把 `.contextproof/pr-comment.md` 作为本地 PR review 摘要。

如果要在 PR 工作流中对比当前分支和 base ref：

```bash
contextproof audit . --pr-comment --changed-against origin/main...HEAD
```

## 它审计什么

| 审计对象 | 不审计 |
| --- | --- |
| coding agent 实际会读取的持久指令 | 普通项目文档 |
| `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` | 普通 README 或设计文档 |
| `.cursor/rules/*.{md,mdc,txt}` | 不会进入 agent context 的 Markdown |
| `.github/copilot-instructions.md` | 没有保存成 context 文件的一次性聊天提示词 |
| `SKILL.md`、MCP notes、agent notes | 未保存为 context 文件的原生 `/init` 输出 |

ContextProof 不会自动运行 Codex、Claude Code、OpenCode、Cursor、Gemini、Copilot 或 Pi。
它审计本地 context 文件，并生成本地报告。

## 核心产物

ContextProof 会在 `.contextproof/` 下生成：

- `report.json`：机器可读审计结果
- `report.md`：人类可读审计报告
- `pr-comment.md`：可复制到 PR 的本地评论文本

静态审计会报告：

- 六个维度评分：可发现性、可执行性、精简度、一致性、安全性、工作流匹配度
- 模糊规则、过度宽泛探索、危险 shell、类似 prompt injection 的语言、重复规则、矛盾规则、缺失验收命令和过大的 context
- 需要人类或 agent 继续检查的建议方向

## 安装 Skill

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

| Agent 表面 | 推荐方式 |
| --- | --- |
| Codex | 原生 skill 路径 |
| Claude Code | 原生或项目内 skill 路径 |
| OpenCode | 原生或项目内 skill 路径 |
| Cursor、Windsurf、Pi | 直接给 agent skill 文件夹路径 |
| 任意可运行 shell 的 agent | 使用 CLI fallback |

路径提示词：

```text
Use the ContextProof skill at /path/to/ContextProof/skill/context-proof.
Audit this repository's agent context. Generate .contextproof/report.md and
.contextproof/pr-comment.md. Do not overwrite existing context files.
```

更多提示词见 [Usage By Agent](docs/USAGE_BY_AGENT.md)。

## 可选 CLI

当你需要 shell 命令、CI job，或 agent 无法直接加载 skill 时，可以安装 CLI。

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

## 项目模式

| 模式 | 何时使用 | V0.2 行为 |
| --- | --- | --- |
| `existing_project` | 仓库已经有代码和工作流 | 默认审计模式 |
| `new_project` | 正在启动一个新仓库 | 缺失 context 时严重级别较低 |
| `migration_project` | 在不同 agent 或技术栈之间迁移规则 | 用于报告和 benchmark 标记 |

示例：

```bash
python -m contextproof.cli audit . --project-mode new_project --pr-comment
```

## 高级用法

### Benchmark 证据

ContextProof 区分静态 hygiene 和行为证据。静态分数不证明 agent 一定表现更好。
行为结论需要真实记录的成对 run 数据。

标准变体：

- `none`：不注入仓库 context
- `current`：仓库当前 context 文件
- `native-init`：工具通过 `/init` 类流程生成的默认 context
- `contextproof-reviewed`：人类或 agent 阅读 ContextProof findings 后明确修改过的 context

汇总本地 JSONL：

```bash
contextproof summarize-runs examples/benchmark-runs.jsonl \
  --md-out .contextproof/benchmark-summary.md
```

把已记录 runs 合并进审计报告：

```bash
contextproof audit . --runs examples/benchmark-runs.jsonl --pr-comment
```

### 起始脚手架

`contextproof minimize` 只在显式请求时生成通用起始脚手架。它不是项目级自动改写结果，也不会替换现有 context 文件。

```bash
contextproof minimize . --output AGENTS.starter.md
```

### CI

严格 CI gate 是可选项：

```bash
contextproof audit . --fail-under 70 --pr-comment
```

默认 GitHub workflow 只上传 artifact，不因为静态分数失败而阻断 PR，除非显式添加 `--fail-under`。
该 workflow 默认只在 agent-context 文件变更时运行。

### Baseline 报告

把当前审计结果和之前保存的 report 对比：

```bash
contextproof audit . --baseline .contextproof/report.main.json --pr-comment
```

PR comment 会包含分数变化、新增 findings 和已解决 findings。

## 仓库结构

```text
contextproof/                 Python package 和 CLI 实现
skill/context-proof/          可移植 agent skill
schemas/                      报告与 benchmark run 的 JSON schema
examples/                     示例 benchmark JSONL 与 demo fixture
integrations/                 不同 agent 的可选命令模板
tests/                        单元测试
```

## 参考资料

- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [OpenCode Agent Skills](https://opencode.ai/docs/skills/)

## 许可证

MIT
