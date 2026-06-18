# AGENTS.md

## Scope

These instructions apply repo-wide.

## Safety

- Do not pipe remote install scripts into a shell.
- Do not make directories world-writable as a permission workaround.
- Do not hide repository instructions from the user.
- Ask before running destructive, privileged, or network installation commands.

## Validation

- Code changes: `pytest`.
- If validation cannot run, report the reason.
