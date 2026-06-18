# Context Optimizer

Use this reference when the user asks ContextProof to improve, tighten, reduce,
or optimize coding-agent context.

## Objective

Create a safer, shorter, more executable candidate context document for a
coding agent. The candidate should reduce context waste and ambiguity while
preserving project-specific operating constraints.

The optimized candidate is a draft. It must be written under
`.contextproof/candidates/` unless the user explicitly asks for another path.
Never overwrite source context files without explicit approval.

## Inputs

Before drafting a candidate:

1. Run the ContextProof audit.
2. Read `.contextproof/report.md` or the JSON findings.
3. Read the source context file or files.
4. Identify which content is actually loaded as coding-agent context.
5. Ignore ordinary README or design documentation unless it is explicitly
   injected into an agent prompt.

## Preserve

Preserve these unless clearly obsolete:

- validation commands, including test, lint, typecheck, build, and check
  commands
- project-specific paths, package names, services, apps, and workspaces
- safety boundaries, approval requirements, and destructive-operation rules
- repository-specific build or dependency constraints
- generated-file and vendored-directory boundaries
- agent-specific conventions that are still active

## Improve

Prefer these transformations:

- Replace vague rules with concrete commands, paths, or acceptance criteria.
- Convert "always read the whole repository" into relevance-based exploration.
- Deduplicate repeated rules across files.
- Merge conflicting instructions into one conditional rule.
- Remove obvious generic advice such as "write clean code" when it adds no
  executable constraint.
- Move rare or conditional details out of top-level context when a referenced
  doc is enough.
- Keep the top-level context short enough to be carried on every coding task.

## Reject

Do not produce a candidate that:

- deletes all validation commands
- deletes important project-specific paths or package names
- makes dangerous shell commands easier to run
- hides safety or approval requirements
- turns static hygiene into a claim of proven agent performance
- rewrites ordinary documentation that is not agent context

## Candidate Output

Write the candidate as a normal Markdown context file, then report:

- source file path
- candidate file path
- what was preserved
- what was removed or compressed
- unresolved findings
- any requirements that need manual review

After writing the candidate, run:

```bash
python scripts/contextproof.py compare-context SOURCE_PATH CANDIDATE_PATH
```

Use the candidate report to decide whether the draft is improved, mixed, or a
regression.
