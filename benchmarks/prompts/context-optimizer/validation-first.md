# Validation-First Optimizer Prompt

Optimize agent-facing context around executable validation and acceptance
criteria.

Priorities:

- Preserve and clarify test, lint, typecheck, build, and check commands.
- Add honest validation placeholders only when the source clearly lacks them.
- Convert vague quality expectations into observable acceptance checks.
- Preserve safety boundaries and project-specific facts.
- Remove broad exploration mandates and generic best-practice language.
- Run `contextproof compare-context SOURCE CANDIDATE` after drafting.

Reject the candidate if validation becomes weaker or less discoverable.
