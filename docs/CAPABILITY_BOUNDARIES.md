# Capability Boundaries

ContextProof should stay a small, skill-first product. The normal user should
install the skill, ask a coding agent to audit and optimize agent context, then
review generated candidates under `.contextproof/`.

## Core User Loop

| Step | Purpose | Boundary |
| --- | --- | --- |
| `prepare-workflow` | Discover, audit, classify, route, and write the workflow packet | Prepares the active coding agent; does not draft or overwrite source files |
| candidate draft | Create an optimized context candidate | Written by the coding agent under `.contextproof/candidates/` |
| `review-candidate` | Check original vs candidate and summarize adoption blockers | Detects score/token/preservation regressions; not proof of real agent performance |

This loop is the product. Everything else supports maintenance, evaluation, or
fallback usage.

See [Product Strategy](PRODUCT_STRATEGY.md) for the separation between
user-facing product work and maintainer-only development work.

## Maintainer-Only Loop

| Step | Purpose | Boundary |
| --- | --- | --- |
| `evaluate-gold` | Test fixture candidates against curated references | Built-in scenarios only; gold is not a user-project answer |
| `benchmark-optimizer` | Compare optimizer prompt variants | Uses existing candidate files; does not call an LLM |
| `calibrate-scorer` | Check deterministic scoring rules | Focused on agent-context issues; not broad Markdown linting |
| `acceptance_v06.py` | Release gate | Local maintainer flow; not required for normal users |

Baseline comparisons, optimizer variants, gold candidates, scorer calibration,
and acceptance scripts are for improving ContextProof itself. They should not
be required in the normal user workflow.

## Current Size Profile

The installed skill is intentionally local-first and self-contained:

- bundled deterministic runner: about 140 KB
- top-level `SKILL.md`: should stay short because agents may read it first
- references and templates: loaded only when the workflow needs them
- examples, gold candidates, calibration cases, and acceptance scripts live
  outside the installed skill's hot path

The runner is the main on-disk cost, but it should not be pasted into the model
context. The prompt-cost risk is `SKILL.md` and any eagerly-read references.

## Keep

- One default user prompt.
- One no-overwrite candidate path: `.contextproof/candidates/`.
- Scenario routing by agent-context use case.
- Deterministic local checks.
- Small scenario templates loaded on demand.
- Maintainer fixtures for gold, calibration, and acceptance.

## Avoid

- Putting benchmark, calibration, or acceptance details in the first user path.
- Adding industry-specific template libraries.
- Turning ContextProof into a general Markdown style checker.
- Adding a hosted service, dashboard, or PR automation as the core product.
- Adding LLM judge logic before deterministic checks are exhausted.
- Expanding `SKILL.md` with content that belongs in references.

## Candidate Simplifications

These are acceptable future simplifications if the skill starts feeling heavy:

- Keep `SKILL.md` under roughly 4 KB.
- Split maintainer-only references into repository docs rather than installed
  skill references.
- Keep only the six scenario templates in the installed skill.
- Keep examples and calibration fixtures outside `skill/context-proof/`.
- Prefer one bundled runner over multiple shell wrappers inside the skill.
- Avoid adding agent-specific instructions unless they change loader paths or
  invocation style.

## Non-Negotiable Guardrails

- Never overwrite source context files by default.
- Never present gold references as real-project answers.
- Never claim real coding-agent performance improvement from static scores.
- Never optimize ordinary documentation unless it is loaded as agent context.
