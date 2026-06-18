# AGENTS.md

## Scope

These instructions apply to invoice workflow changes.

## Working Rules

- Keep changes scoped to the requested task.
- Move non-operational business notes out of persistent agent context unless they constrain the current code change.

## Validation

- Invoice workflow changes: `pytest tests/invoices`.
- If tests cannot run, report the reason.
