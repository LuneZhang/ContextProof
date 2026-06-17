---
description: Audit repository agent context with ContextProof
argument-hint: [repo-path]
---

Use the context-proof skill if it is installed. If it is not installed, read
`skill/context-proof/SKILL.md` from the ContextProof repository and follow its
workflow.

Use `$ARGUMENTS` as the repository path when it is provided; otherwise use `.`.
Run:

```bash
contextproof audit . --pr-comment --minimize
```

If the `contextproof` command is unavailable, use:

```bash
python -m contextproof.cli audit . --pr-comment --minimize
```

Summarize the static score, confidence state, critical/high findings, and files
written under `.contextproof/`. Do not overwrite existing context files.
