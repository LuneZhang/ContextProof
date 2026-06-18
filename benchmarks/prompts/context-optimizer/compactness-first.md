# Compactness-First Optimizer Prompt

Draft the shortest candidate context that preserves the source file's
operational value for a coding agent.

Priorities:

- Preserve concrete commands and project paths.
- Collapse repeated directory maps and repeated rules.
- Remove generic prose, motivational language, and obvious coding advice.
- Prefer terse bullets over paragraphs.
- Keep validation and safety sections explicit.
- Run `contextproof compare-context SOURCE CANDIDATE` after drafting.

Reject the candidate if it removes validation commands, project-specific paths,
or safety boundaries.
