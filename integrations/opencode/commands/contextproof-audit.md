---
description: Audit repository agent context with ContextProof
---

Load the context-proof skill if available. Audit the repository path from
`$ARGUMENTS`, or the current working directory when no argument is provided.

Use `$ARGUMENTS` as the repository path when it is provided; otherwise use `.`.
Run:

```bash
contextproof audit . --pr-comment --minimize
```

If the CLI is not installed, run:

```bash
python -m contextproof.cli audit . --pr-comment --minimize
```

Report the static score, confidence state, critical/high findings, and generated
files. Do not overwrite existing context files.
