# TODO

This document is the V0.3 implementation checklist. V0.3 must stay focused on
ContextProof's real product core: optimizing persistent Markdown context for
coding agents.

## Product Essence

ContextProof is a coding-agent context optimization skill.

The target input is not arbitrary Markdown. The target input is Markdown that a
coding agent reads before or during code edits:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.cursor/rules/*`
- `.github/copilot-instructions.md`
- `SKILL.md`
- MCP notes
- saved `/init` repository briefs
- project-local agent rules for OpenCode, Codex, Claude Code, Cursor,
  Windsurf, Pi, and similar tools

The user should install the skill, then ask their coding agent to audit and
improve those files in natural language. The deterministic CLI is the runner
behind the skill, not the product's primary identity.

## What V0.3 Must Improve

V0.1 and V0.2 built the deterministic auditor. V0.3 should build the
optimization loop around that auditor:

1. Scenario fixtures: realistic bad, bloated, conflicting, or vague agent
   context documents.
2. Optimizer prompt: the instructions the coding agent uses to produce a better
   candidate context document.
3. Candidate safety: optimized drafts are written to `.contextproof/candidates/`
   and never overwrite source files automatically.
4. Candidate evaluation: compare original versus candidate with static score,
   token/length delta, issue delta, preserved requirements, and unresolved
   risks.
5. Prompt iteration benchmark: run the same scenario fixtures against optimizer
   prompt variants so we can improve the optimizer instead of guessing.

## Definition Of Done

V0.3 is complete when a user can:

- Ask a coding agent to use ContextProof to optimize repository agent context.
- Receive an optimized candidate file without losing the original context file.
- See exactly which problems were fixed, which remain, and which requirements
  were preserved.
- Compare before and after scores and approximate token cost.
- Run the included scenario fixtures to evaluate whether a prompt change made
  the optimizer better.
- Understand that ContextProof optimizes agent-facing context quality, not
  general project documentation.

## V0.3.0: Scenario Corpus

Goal: create the testbed used to improve the optimizer prompt.

### Fixtures To Add

- [x] `examples/scenarios/existing-project-overbroad/`
  - A realistic `AGENTS.md` that asks the agent to read the whole repo,
    over-explains obvious rules, and lacks targeted validation.
- [x] `examples/scenarios/existing-project-conflicting/`
  - Context files with contradictory instructions, duplicated rules, and mixed
    agent-specific conventions.
- [x] `examples/scenarios/new-project-init-brief/`
  - A saved `/init`-style project brief for a new repository. It should be
    useful but too verbose and weak on acceptance criteria.
- [x] `examples/scenarios/multi-agent-migration/`
  - A project with `AGENTS.md`, `CLAUDE.md`, and `.cursor/rules` that overlap
    and drift from each other.
- [x] `examples/scenarios/unsafe-automation/`
  - Context that includes dangerous shell shortcuts, implicit network install
    commands, and unclear permission boundaries.
- [x] `examples/scenarios/missing-validation-criteria/`
  - Context that asks for quality and caution but provides no concrete
    validation command or acceptance check.
- [x] `examples/scenarios/misplaced-general-documentation/`
  - Context that pastes ordinary product or planning notes into persistent
    agent instructions.
- [x] `examples/scenarios/token-heavy-monorepo/`
  - A long monorepo context document with repeated directory maps, duplicated
    workflows, and irrelevant prose.

### Fixture Metadata

Each scenario should include:

- [x] `README.md`: what the scenario represents.
- [x] `source/`: original context files.
- [x] `expected.json`: expected issue categories and preservation requirements.
- [x] `notes.md`: why the fixture matters and what a good optimizer should do.

### Expected Issue Categories

- [x] vague or non-verifiable instruction
- [x] overbroad repository exploration
- [x] missing validation command
- [x] unsafe shell or install guidance
- [x] conflicting instruction
- [x] duplicated instruction
- [x] oversized or token-wasteful context
- [x] misplaced general documentation

## V0.3.1: Optimizer Prompt Pack

Goal: make the skill's optimizer instructions a first-class artifact.

### Skill Files

- [x] Add `skill/context-proof/references/context-optimizer.md`.
- [x] Add `skill/context-proof/references/optimization-checklist.md`.
- [x] Update `skill/context-proof/SKILL.md` with an explicit optimization
  workflow.

### Optimizer Prompt Contract

The optimizer prompt must instruct the coding agent to:

- [x] Read ContextProof findings first.
- [x] Identify which context files are actually agent-facing.
- [x] Preserve project-specific commands, paths, architecture facts, and safety
  constraints.
- [x] Remove or tighten vague rules.
- [x] Convert broad mandates into task-scoped behavior.
- [x] Add or preserve concrete validation commands.
- [x] Deduplicate repeated instructions.
- [x] Separate stable project rules from one-off task notes.
- [x] Reduce token load without deleting essential operating constraints.
- [x] Write candidates under `.contextproof/candidates/`.
- [x] Produce a concise rationale and unresolved-risk list.
- [x] Never overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or
  other source context files unless the user explicitly approves.

### Output Format

The optimizer should produce:

- [x] candidate file path
- [x] source file path
- [x] high-level transformation summary
- [x] preserved requirements
- [x] removed or compressed sections
- [x] unresolved findings
- [x] suggested next manual review step

## V0.3.2: Candidate Evaluation

Goal: compare the original context and optimized candidate without relying on
trust or vibes.

### CLI Or Runner Capability

- [x] Add a candidate comparison command or mode.
  - Candidate name can be `contextproof compare-context`.
  - Alternative: add `contextproof audit --candidate PATH`.
  - Choose the smaller implementation after reading the existing CLI structure.
- [x] Compare source and candidate with the same deterministic auditor.
- [x] Report before score, after score, and score delta.
- [x] Report finding counts by severity before and after.
- [x] Report approximate token or character delta.
- [x] Report preserved explicit commands and paths where detectable.
- [x] Report new risks introduced by the candidate.
- [x] Write `.contextproof/candidate-report.json`.
- [x] Write `.contextproof/candidate-report.md`.

### Evaluation Metrics

- [x] static score delta
- [x] critical/high finding delta
- [x] approximate token delta
- [x] validation-command preservation
- [x] path/command preservation
- [x] unresolved issue list
- [x] newly introduced issue list

### Safety Contract

- [x] Candidate evaluation must never write over source context files.
- [x] If a candidate removes all validation commands, flag it as a regression.
- [x] If a candidate removes all project-specific paths or commands, flag it for
  manual review.
- [x] If a candidate improves brevity but increases safety risk, do not label it
  as a clean improvement.

## V0.3.3: Prompt Variant Benchmark

Goal: make optimizer prompt iteration measurable.

### Prompt Variants

- [x] Store optimizer prompt variants under
  `benchmarks/prompts/context-optimizer/`.
- [x] Keep a canonical baseline prompt.
- [x] Keep experiment prompts small and named by intent, for example:
  `compactness-first.md`, `validation-first.md`, `migration-aware.md`.

### Benchmark Runner

- [x] Add a lightweight script or command that records scenario results for a
  prompt variant.
- [x] The runner may be semi-manual if the active coding agent performs the LLM
  rewrite step.
- [x] Record results as JSONL using the existing benchmark style where possible.
- [x] Include scenario id, prompt variant, source file, candidate file, score
  delta, token delta, preserved requirements, and regression flags.

### Benchmark Acceptance

- [x] A prompt variant is better only if it improves or preserves:
  - score delta
  - critical/high finding reduction
  - token delta
  - validation-command preservation
  - safety risk count
- [x] A prompt variant that deletes important project constraints is worse even
  if it shortens the file.

## V0.3.4: User-Facing Workflow

Goal: make the actual skill workflow obvious.

### README Changes

- [x] Move "optimize agent context" to the primary README flow.
- [x] Show a copyable prompt:

```text
Use $context-proof to audit and optimize this repository's agent context.
Write optimized drafts under .contextproof/candidates/.
Do not overwrite source context files.
Then compare the original and candidate and report score delta, token delta,
preserved requirements, unresolved risks, and generated files.
```

- [x] Keep CLI as a fallback runner, not the headline.
- [x] Explain that ContextProof does not optimize ordinary docs.
- [x] Explain that static score is hygiene evidence, not proof of real coding
  performance.

### Chinese README Changes

- [x] Mirror the primary workflow in Chinese.
- [x] Clarify the product promise in Chinese:
  ContextProof optimizes Markdown context that coding agents actually read.

### Skill Usage Docs

- [x] Update `docs/USAGE_BY_AGENT.md` to show the optimize workflow for Codex,
  Claude Code, OpenCode, Cursor, Windsurf, and Pi.
- [x] Update `docs/AGENT_INSTALL_PROMPT.md` so installation flows into audit,
  candidate generation, and candidate evaluation.

## V0.3.5: Release Hardening

Goal: ship the optimizer loop without broadening scope.

### Required Tests

- [x] Existing unit tests still pass:
  `python -m unittest discover -s tests`.
- [x] Each scenario fixture produces expected issue categories.
- [x] Candidate comparison catches a deliberately bad "short but unsafe"
  candidate.
- [x] Candidate comparison catches a candidate that deletes validation commands.
- [x] Candidate comparison marks a genuinely improved fixture candidate as
  improved.
- [x] Standalone skill script still runs outside the repository.
- [x] Install script smoke tests still pass or skip appropriately by platform.

### Required Demos

- [x] Demo: bad context -> optimized candidate -> improved candidate report.
- [x] Demo: new-project init brief -> tighter agent context candidate.
- [x] Demo: multi-agent migration -> reduced duplication candidate.

### Release Tasks

- [x] Bump package version to `0.3.0`.
- [x] Bump skill metadata version to `0.3.0`.
- [x] Bump report schema version to `0.3.0` for V0.3 outputs.
- [x] Update `CHANGELOG.md`.
- [x] Tag `v0.3.0`.
- [x] Push `main` and the tag.

## Explicit Non-Goals For V0.3

- [x] GitHub Action packaging as the main feature.
- [x] Hosted dashboards.
- [x] Browser UI.
- [x] Automatic source-file replacement.
- [x] PyPI publishing unless needed for installation clarity.
- [x] General Markdown linting.
- [x] Broad static-rule expansion unrelated to candidate optimization.
- [x] Claims of real coding-agent performance improvement without behavioral
  benchmark evidence.

## Later Versions

- V0.4: distribution surfaces such as GitHub Actions and PR comments.
- V0.5: native `/init` baseline collectors for different agents.
- V0.6: larger scorer calibration and optional LLM advisory workflows.
