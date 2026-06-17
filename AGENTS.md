# AGENTS.md

## Scope

These instructions apply to the whole repository.

## Working Rules

- Keep static audit behavior deterministic by default.
- Do not claim static scores prove behavioral agent performance.
- Keep the skill folder portable: `skill/context-proof/SKILL.md` is the primary artifact.
- Treat generated `.contextproof/` files as local output unless a task explicitly asks to commit examples.

## Validation

- Run tests with `python -m unittest discover -s tests`.
- Run a self-audit with `python -m contextproof.cli audit . --pr-comment --minimize --deterministic`.
