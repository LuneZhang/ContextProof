# Roadmap

ContextProof has three separate development tracks:

- product track: improve the installed skill and the normal user workflow
- evaluation track: improve scorer, optimizer prompts, fixtures, and release
  confidence
- distribution track: improve installation and review surfaces

The product track is primary. Evaluation and distribution work must not become
required steps in the normal user workflow. See
[Product Strategy](PRODUCT_STRATEGY.md) for the boundary.

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

## V0.4 Scenario Router And Template-Guided Optimization

Status: complete.

V0.4 adds the missing routing layer between static audit findings and the
optimizer prompt. ContextProof should not rely on one universal rewrite prompt
for every agent-context file. It should first classify the user's actual
context scenario, then select a focused optimizer template.

### Product Objective

- A user can classify an agent-facing context file or context directory before
  asking the coding agent to rewrite it.
- The skill selects an optimizer template based on agent-context scenario, not
  on business domain or generic Markdown type.
- The generated route tells the coding agent what to preserve, what to remove,
  and which scenario-specific template to read.
- Optimizer benchmarks are grouped by classified scenario route, so prompt
  changes can be judged per scenario instead of only by aggregate score.

### Primary Deliverables

- `classify-context` command for scenario classification.
- `route-optimizer` command for generating `.contextproof/optimizer-instructions.md`.
- Classifier reference and optimizer templates for:
  - new-project `/init` summaries
  - existing-project agent rules
  - multi-agent context migration
  - workflow or SOP context
  - safety-sensitive context
  - token-heavy context
- Scenario fixture metadata with expected primary routes.
- Optimizer benchmark route summaries and classification match rates.
- README and skill workflow updates for classify -> route -> candidate ->
  compare.

### Non-Goals For V0.4

- Do not create an industry template library.
- Do not automatically rewrite or replace source context files.
- Do not use the classifier as proof that a candidate is good.
- Do not move the product center to CI, GitHub Actions, or hosted dashboards.

## V0.5 Scorer Calibration And Gold Candidates

Status: complete.

V0.5 calibrates ContextProof's judgment loop. It does not expand the product
into CI, dashboards, industry template libraries, or a generic Markdown linter.

### Product Objective

- Use curated gold/reference candidates to test whether optimized agent context
  preserved project constraints while removing the intended issues.
- Catch bad candidates that get shorter by deleting validation commands, path
  anchors, or safety boundaries.
- Calibrate deterministic scoring against focused agent-context examples.
- Provide a repeatable local acceptance flow that maintainers can run before
  changing optimizer prompts or scorer rules.

### Primary Deliverables

- Gold candidates for all eight built-in scenarios under
  `examples/scenarios/*/gold/AGENTS.gold.md`.
- `evaluate-gold` for source-vs-candidate-vs-gold evaluation.
- Optimizer benchmark gold fields and aggregate gold alignment metrics.
- `examples/calibration/cases.jsonl` plus `calibrate-scorer`.
- `scripts/acceptance_v05.py` and `make acceptance`.
- Standalone skill runner support for the new v0.5 commands.

### Non-Goals For V0.5

- Do not use an LLM judge.
- Do not claim real coding-agent performance gains without behavioral runs.
- Do not turn gold candidates into automatic answers for user repositories.
- Do not broaden deterministic rules beyond what candidate evaluation needs.

## V0.5.1 Skill-First Adoption Polish

Status: complete.

V0.5.1 makes the product easier to understand without adding new evaluation
surface area.

### Product Objective

- Make the first user action obvious: install the skill and ask the coding
  agent to audit and optimize repository agent context.
- Keep the normal path short while preserving maintainer workflows for gold,
  calibration, benchmark, and acceptance.
- Reduce prompt-load risk by keeping `SKILL.md` concise and moving detail into
  references or repository docs.

### Primary Deliverables

- Skill-first README and Chinese README.
- Shorter `skill/context-proof/SKILL.md`.
- `docs/CAPABILITY_BOUNDARIES.md` for capability limits and size-control rules.
- Version metadata update to `0.5.1` while keeping report schema `0.5.0`.

### Non-Goals For V0.5.1

- Do not add new deterministic rules.
- Do not expand scenario templates.
- Do not add CI, dashboard, hosted service, or LLM judge behavior.

## V0.6 Skill Runtime UX And One-Prompt Optimization Flow

Status: complete.

V0.6 should make ContextProof feel like one focused, installable skill rather
than a command collection. The goal is to make the normal user path reliable:
ask the active coding agent to audit and improve agent context, produce a
candidate, compare it, and stop before overwriting source files.

### Product Objective

- A new user can install the skill and use one natural-language prompt to start
  the full workflow.
- ContextProof can discover likely agent-context files in a repository and
  explain which files are in scope.
- The workflow produces one clear work packet under `.contextproof/`: audit,
  classification, optimizer instructions, candidate path, and comparison.
- The active coding agent receives enough instructions to draft a good
  candidate without reading maintainer-only benchmark material.
- Candidate comparison remains the user's decision point. Source context files
  are never overwritten by default.

### Primary Deliverables

- A single user-facing workflow command or skill-runner flow that performs:
  discover -> audit -> classify -> route -> write optimizer packet.
- Repository context discovery for supported agent files:
  `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/*`,
  `.github/copilot-instructions.md`, `SKILL.md`, MCP notes, and saved `/init`
  briefs.
- A concise `.contextproof/workflow.md` that tells the active coding agent
  exactly what to do next and where to write candidates.
- A consolidated comparison summary that is easier for users to review than
  separate raw reports.
- Stronger checks around no-overwrite behavior, source/candidate path hygiene,
  missing validation commands, negated validation commands, and removed project
  path anchors.
- README, Chinese README, usage docs, and skill instructions updated around
  the one-prompt flow.
- Standalone skill runner support for v0.6 commands.
- `scripts/acceptance_v06.py` or an equivalent extension that keeps v0.5
  acceptance checks and adds one-prompt workflow checks.

### Non-Goals For V0.6

- Do not make users run gold evaluation, scorer calibration, benchmark
  variants, or acceptance scripts.
- Do not ask users to collect baselines for ContextProof development.
- Do not automate external coding agents.
- Do not add a hosted service, dashboard, or CI workflow.
- Do not add business-domain or industry template libraries.
- Do not claim real task-performance improvement from static scores.
- Do not optimize ordinary Markdown that is not loaded as agent context.

## V0.7 Distribution And Review Surfaces

- GitHub Action packaging.
- Optional PR comment posting.
- Score trend reports.
- Comment-only default with explicit opt-in gates.
- Keep these as distribution surfaces, not the primary product loop.

## V0.8 Behavioral Evidence

- Real paired coding-agent task runs across `none`, `current`,
  `native-init`, and `contextproof-reviewed`.
- Per-scenario behavioral evidence reports.
- Optional LLM advisory annotations after deterministic metrics are recorded.
- No claim of real performance improvement without paired behavioral data.

See [TODO](TODO.md) for the detailed current implementation checklist.
