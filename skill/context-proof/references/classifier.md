# Context Classifier

Use this reference when ContextProof needs to route an optimization request to a
scenario-specific optimizer template.

## Classification Goal

Classify the role of the agent-facing context before rewriting it. The
classification selects the optimization prompt template. It does not replace
the audit and it does not decide whether the candidate is acceptable.

## Supported Scenarios

- `new-project-init-summary`: saved `/init` or repository-overview context for
  a new project. Emphasize repository map, commands, and acceptance criteria.
- `existing-project-agent-rules`: established `AGENTS.md`, `CLAUDE.md`, or
  equivalent persistent rules. Emphasize executable rules and validation.
- `multi-agent-context-migration`: overlapping rules across multiple agent
  surfaces. Emphasize deduplication, conflict resolution, and canonical output.
- `workflow-sop-context`: repeatable release, review, deploy, or validation
  workflows. Emphasize ordered steps, preconditions, commands, and outcomes.
- `safety-sensitive-context`: production, database, secrets, deploy, deletion,
  migration, or destructive-operation context. Emphasize negative constraints
  and approval gates.
- `token-heavy-context`: long or repetitive context with low information
  density. Emphasize compression and preservation checks.

## Routing Rule

Prefer the scenario that most changes the optimizer strategy. For example,
unsafe production database instructions should route to
`safety-sensitive-context` even if the file is also long.

Use secondary scenarios to keep important optimization pressure visible. A
token-heavy migration can route primarily to `multi-agent-context-migration`
with `token-heavy-context` as a secondary scenario.

## Output Contract

The classifier should produce:

- primary scenario
- secondary scenarios
- document role
- selected template
- optimization focus
- risk level
- evidence for the routing decision

The optimizer should then read the selected template and write a candidate
under `.contextproof/candidates/` without overwriting source context files.
