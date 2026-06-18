# Migration-Aware Optimizer Prompt

Optimize context for repositories that use multiple agent surfaces.

Priorities:

- Identify overlapping rules across `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`,
  `SKILL.md`, and other agent-facing files.
- Preserve the active source of truth for validation and project paths.
- Remove duplicated rules or make agent-specific differences explicit.
- Resolve contradictions into conditional rules.
- Keep candidates under `.contextproof/candidates/`.
- Run `contextproof compare-context SOURCE CANDIDATE` after drafting.

Reject the candidate if it hides a meaningful agent-specific convention.
