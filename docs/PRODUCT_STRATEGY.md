# Product Strategy

ContextProof is a skill-first product for improving persistent Markdown context
that coding agents actually read.

The product and the maintainer development loop are separate. User-facing
features should make the skill easier, safer, and more useful in real
repositories. Maintainer tools should improve ContextProof's own scorer,
optimizer prompts, scenario fixtures, and release confidence.

## Product Positioning

ContextProof helps a developer ask their current coding agent to audit and
improve agent-facing context files.

Primary targets:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.cursor/rules/*`
- `.github/copilot-instructions.md`
- `SKILL.md`
- MCP notes
- saved `/init` repository briefs

ContextProof is not a general Markdown linter, a documentation writer, a
dashboard, a hosted service, or an agent automation platform.

## User-Facing Product Loop

The normal user experience should stay short:

1. Install the `context-proof` skill.
2. Ask the active coding agent to use ContextProof on the repository's agent
   context.
3. ContextProof runs `prepare-workflow` to discover, audit, classify, and route
   the source context.
4. The workflow packet routes the active agent to the right optimizer template.
5. The active agent writes a candidate under `.contextproof/candidates/`.
6. ContextProof runs `review-candidate` to compare original and candidate.
7. The user reviews the report and manually decides whether to adopt the
   candidate.

The product must not require the user to understand gold candidates, scorer
calibration, benchmark variants, or acceptance scripts.

## Maintainer Development Loop

Maintainer tools exist to improve ContextProof itself:

- scenario fixtures test common agent-context failure modes
- gold candidates test whether candidates preserve constraints
- scorer calibration tests deterministic rules
- optimizer benchmarks compare prompt/template variants
- acceptance scripts guard release quality

These tools should stay in maintainer docs and tests. They should not appear as
required steps in the normal user workflow.

## Boundary Rules

- User features must help the installed skill complete the audit, route,
  candidate, and compare workflow.
- Maintainer features must be labeled as maintainer-only and should not be
  promoted as user value.
- ContextProof can compare files locally, but it should not ask normal users to
  run baseline experiments for product development.
- Baseline or behavioral evidence work belongs to maintainer research until it
  becomes a simple, optional user report.
- No feature should overwrite source context files by default.
- No feature should claim real coding-agent task performance gains from static
  scores alone.

## Development Tracks

### Product Track

Improves the skill users install and invoke in a coding-agent environment.

Examples:

- clearer one-prompt workflow
- automatic source context discovery
- better optimizer instruction packet
- better candidate comparison report
- safer no-overwrite behavior
- smaller skill hot path

### Evaluation Track

Improves ContextProof's internal judgment and release quality.

Examples:

- gold candidate evaluation
- scorer calibration
- benchmark prompt variants
- fixture expansion
- acceptance scripts
- cross-review gates

### Distribution Track

Improves installation and review surfaces without changing the core product
loop.

Examples:

- skill installers
- optional GitHub Action packaging
- optional PR comment output
- release hygiene

Distribution must not replace the skill-first product identity.
