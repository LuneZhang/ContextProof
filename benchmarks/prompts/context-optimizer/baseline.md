# Baseline Context Optimizer Prompt

Use ContextProof findings to draft a concise, safer candidate for agent-facing
Markdown context.

Rules:

- Preserve validation commands, project paths, package names, safety boundaries,
  and active agent-specific conventions.
- Remove generic quality advice that cannot be tested.
- Replace repository-wide exploration mandates with task-scoped discovery.
- Deduplicate repeated rules and resolve contradictions.
- Reduce token load only when essential project constraints remain intact.
- Write the candidate under `.contextproof/candidates/`.
- Never overwrite source context files without explicit user approval.
- After drafting, run `contextproof compare-context SOURCE CANDIDATE` and treat
  regression flags as blockers.
