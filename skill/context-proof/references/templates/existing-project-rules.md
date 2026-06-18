# Existing Project Rules Template

Use this template for established repository-level agent rules such as
`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules`, or similar files.

## Optimization Goal

Make persistent agent instructions executable, verifiable, concise, and
repository-specific.

## Keep

- Explicit validation commands.
- Current repo paths, package names, services, and workspaces.
- Safety rules that prevent real recurring mistakes.
- Agent loader conventions that determine which files are read.

## Rewrite Strategy

- Remove generic quality advice such as "write clean code" unless it includes
  a concrete check.
- Convert "always read the whole repository" into task-scoped discovery.
- Merge duplicate rules.
- Resolve conflicting rules into one conditional rule.
- Prefer direct commands and acceptance criteria over abstract principles.
- Keep negative constraints only when they protect real systems, data, secrets,
  generated files, or ownership boundaries.

## Candidate Shape

Use sections close to:

1. Scope
2. Project Map
3. Commands
4. Working Rules
5. Safety And Boundaries
6. Validation
7. Context Maintenance

Every rule should answer: what should the agent do, when, and how can the user
verify it happened?
