# AGENTS.md

## Scope

These instructions apply across the monorepo.

## Essential Paths

- Web app: `apps/web`.
- API service: `services/api`.
- Shared UI package: `packages/ui`.
- Shared config package: `packages/config`.

## Working Rules

- Read task-relevant files before broad searches.
- Keep changes scoped to the requested workspace.
- Avoid repeating directory maps; update this file only when a path changes how agents should work.

## Validation

- Code changes: `pnpm test`.
- If only documentation changes, state that tests were not run.
