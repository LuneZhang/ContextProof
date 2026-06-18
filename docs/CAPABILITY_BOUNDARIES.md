# Capability Boundaries

ContextProof should stay a small, skill-first product. The normal user should
install the skill, ask a coding agent to audit and optimize agent context, then
review generated candidates under `.contextproof/`.

## Core User Loop

| Step | Purpose | Boundary |
| --- | --- | --- |
| `audit` | Detect agent-context problems | Deterministic issue detection only; not a rewrite engine |
| `classify-context` | Identify usage scenario | Agent-context scenarios only; not industry/domain classification |
| `route-optimizer` | Select the optimizer template | Produces instructions for the active coding agent; does not rewrite source files |
| candidate draft | Create an optimized context candidate | Written by the coding agent under `.contextproof/candidates/` |
| `compare-context` | Check original vs candidate | Detects score/token/preservation regressions; not proof of real agent performance |

This loop is the product. Everything else supports maintenance, evaluation, or
fallback usage.

## Maintainer-Only Loop

| Step | Purpose | Boundary |
| --- | --- | --- |
| `evaluate-gold` | Test fixture candidates against curated references | Built-in scenarios only; gold is not a user-project answer |
| `benchmark-optimizer` | Compare optimizer prompt variants | Uses existing candidate files; does not call an LLM |
| `calibrate-scorer` | Check deterministic scoring rules | Focused on agent-context issues; not broad Markdown linting |
| `acceptance_v05.py` | Release gate | Local maintainer flow; not required for normal users |

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
