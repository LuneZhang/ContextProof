# Agent Install Prompt

Copy this into a coding agent when you want the agent to install ContextProof
and then use it on the current repository.

```text
Install ContextProof for this coding-agent environment.

Repository: https://github.com/LuneZhang/ContextProof

Goal:
- Install the `context-proof` skill from `skill/context-proof`.
- Prefer the agent's native global skill location when available.
- Otherwise install the skill project-locally.
- Ensure the deterministic runner can execute with Python 3.11+.
- Treat ContextProof as an auditor for agent-facing Markdown context, not as a
  general Markdown optimizer.

After installation, use the context-proof skill to audit and optimize this
repository's agent context. Prepare the workflow packet first, then draft a
candidate from `.contextproof/workflow.md` and
`.contextproof/optimizer-instructions.md`. Generate:
- .contextproof/report.md
- .contextproof/context-discovery.md
- .contextproof/context-classification.md
- .contextproof/optimizer-instructions.md
- .contextproof/workflow.md
- optimized candidate drafts under .contextproof/candidates/
- .contextproof/candidate-review.md

Do not overwrite AGENTS.md, CLAUDE.md, .cursor/rules, SKILL.md, or other
existing context files.

If the skill needs a shell runner, install the repository in editable mode with:
python -m pip install -e .

If the contextproof command is unavailable, run:
python -m contextproof.cli prepare-workflow .

After drafting a candidate, review it with:
python -m contextproof.cli review-candidate SOURCE_CONTEXT_PATH CANDIDATE_CONTEXT_PATH

When reviewing a PR that changes agent context files, preserve the generated
.contextproof/pr-comment.md as the local review summary.
```
