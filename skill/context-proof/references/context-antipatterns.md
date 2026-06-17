# Context Anti-patterns

## Vague Quality Rules

Examples:

- "Follow best practices."
- "Write clean code."
- "Be careful."
- "Make it production ready."

Why it matters: these consume context without changing behavior in a testable
way.

## Over-broad Exploration

Examples:

- "Read the entire repository before every task."
- "Inspect all files before making changes."
- "Always run all tests."

Why it matters: broad instructions increase token cost and may reduce task
focus. Prefer relevance-based exploration and concrete validation commands.

## Conflicting Instructions

Examples:

- "Always ask before editing" and "Never ask questions."
- "Always run tests" and "Do not run tests locally."

Why it matters: agents tend to obey context files. Conflicts waste reasoning and
create inconsistent behavior.

## Unsafe Operational Text

Examples:

- `curl ... | sh`
- `sudo rm -rf`
- `chmod 777`
- "Ignore previous instructions."
- "Read and print all environment variables."

Why it matters: agent context is executable operational influence, not passive
documentation.

