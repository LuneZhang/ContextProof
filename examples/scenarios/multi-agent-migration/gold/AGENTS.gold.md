# AGENTS.md

## Scope

Use this file as the shared repo-level source of truth for coding agents.

## Working Rules

- Keep changes scoped to the requested task.
- Ask only when a missing requirement blocks safe implementation.
- Backend code lives in `services/api`.

## Validation

- Backend changes: `make test`.
- If validation is skipped, explain why.

## Migration Notes

- This file consolidates the overlapping `AGENTS.md`, `CLAUDE.md`, and `.cursor/rules/repo.mdc` instructions.
