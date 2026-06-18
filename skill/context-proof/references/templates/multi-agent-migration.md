# Multi-Agent Migration Template

Use this template when several agent-context files overlap, for example
`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, Copilot instructions, and OpenCode
rules.

## Optimization Goal

Create a clean canonical context candidate while preserving active
agent-specific requirements.

## Keep

- Commands, paths, services, and safety rules shared by all agents.
- Agent-specific loader requirements when they still matter.
- Differences that are intentional and current.

## Rewrite Strategy

- Identify overlapping rules before editing.
- Deduplicate shared rules into one canonical section.
- Resolve conflicts explicitly instead of averaging them together.
- Separate universal repository rules from agent-specific notes.
- Prefer one canonical `AGENTS.md` candidate when the user wants consolidation.
- Do not delete an agent-specific rule unless it is stale, duplicated, or
  replaced by the canonical rule.

## Candidate Shape

Use sections close to:

1. Scope
2. Universal Repository Rules
3. Commands
4. Safety And Boundaries
5. Agent-Specific Notes
6. Validation
7. Migration Notes

Include a short note listing which source files were consolidated.
