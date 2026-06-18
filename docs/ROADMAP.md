# Roadmap

## V0.1 Core

Status: complete.

- Deterministic static audit.
- Local JSON and markdown reports.
- Local PR-comment markdown.
- Optional generic context starter candidate generation.
- Benchmark JSONL summary.
- Portable `context-proof` skill.
- Compatibility docs for Codex, Claude Code, OpenCode, and generic agents.

## V0.1.1 Adoption Hardening

Status: complete.

- Skill-first README.
- Chinese README.
- Demo fixture for a flawed agent context.
- Agent-specific usage prompts.
- Refined reports around deterministic issue detection, evidence, confidence,
  and severity instead of rewrite planning.

## V0.2 Benchmark Evidence

Status: complete.

- Paired benchmark grouping.
- Directional and supported evidence states.
- Baseline comparison across `none`, `current`, `native-init`, and
  `contextproof-reviewed`.
- Better uncertainty reporting.
- `audit --runs` support for merging behavioral evidence into static reports.

## V0.2.1 PR Workflow Hardening

Status: complete.

- Changed agent-context file detection from local git state or a git ref/range.
- Baseline report comparison for score and finding deltas.
- PR comment sections for changed context files and baseline deltas.
- Realistic team-agent-context demo fixture.
- GitHub workflow template scoped to agent-context file changes.

## V0.2.2 Install And Baseline Usability Pass

Status: complete.

- Added smoke coverage for the skill install scripts without touching a real
  global home directory.
- Documented shortcut skill installers for macOS, Linux, WSL, and Windows.
- Documented how to create a saved baseline report before using
  `audit --baseline`.

## V0.3 Context Optimization Engine

Status: complete.

V0.3 should turn ContextProof from a static context auditor into a repeatable
agent-context optimization workflow. The core product is not CI packaging. The
core product is a skill and evaluation loop that helps a coding agent improve
the Markdown context it is about to rely on.

ContextProof should optimize persistent agent-facing Markdown such as
`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, MCP notes, and saved
`/init` briefs. It should not optimize ordinary project documentation.

### Product Objective

- A user can ask their coding agent to audit and improve repository-level
  agent context without overwriting the original files.
- The skill produces a candidate optimized context file, a concise diff-style
  explanation, and an after-audit report.
- The optimizer prompt is treated as a core artifact and is tested against
  scenario fixtures.
- Static scoring remains deterministic, but V0.3 adds candidate comparison:
  before score, after score, token/length delta, preserved requirements, and
  unresolved risks.
- Benchmark scenarios distinguish existing projects, new-project `/init`
  briefs, and migrations between agent surfaces.

### Primary Deliverables

- Scenario fixture corpus for flawed agent-context documents.
- An optimizer prompt pack inside the `context-proof` skill.
- A candidate-generation workflow that writes optimized drafts under
  `.contextproof/candidates/` and never overwrites source context files.
- Candidate comparison reports for original versus optimized drafts.
- Benchmark guidance for testing optimizer prompt variants on the same
  scenario corpus.
- README positioning that makes the product promise clear: improve agent-facing
  context quality, not general Markdown quality and not CI enforcement.

### Non-Goals For V0.3

- Do not build GitHub Action packaging as the main release theme.
- Do not build a web app, dashboard service, or hosted backend.
- Do not optimize arbitrary README or product docs.
- Do not automatically replace user context files.
- Do not claim the optimizer proved real coding-agent performance unless
  behavioral benchmark runs exist.
- Do not tune many more static rules unless they are required to evaluate
  optimized context candidates.

## V0.4 Distribution And Review Surfaces

- GitHub Action packaging.
- Optional PR comment posting.
- Score trend reports.
- Comment-only default with explicit opt-in gates.

## V0.5 Agent Baselines And Scenario Expansion

- Helpers for collecting native `/init` outputs.
- Larger existing-project and new-project scenario fixture sets.
- Agent-specific adapters where stable APIs exist.

## V0.6 Optimization Calibration

- Fixture-driven scorer calibration.
- Optional LLM advisory rewrites that never replace deterministic scoring.
- Behavioral benchmark evidence when real paired agent runs are available.

See [TODO](TODO.md) for the detailed V0.3 implementation checklist.
