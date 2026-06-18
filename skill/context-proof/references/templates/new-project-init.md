# New Project Init Template

Use this template for saved `/init` output, bootstrap notes, or repository
overview context for a new project.

## Optimization Goal

Turn a broad project summary into compact agent onboarding context that helps a
coding agent make its first useful edits without inventing conventions.

## Keep

- Actual package manager, framework, language, service, and workspace names.
- Startup, test, lint, typecheck, and build commands.
- Real source paths and generated or vendored boundaries.
- Known architectural facts that affect edits.

## Rewrite Strategy

- Replace narrative overview with a short repository map.
- Keep only commands the agent can run or report as unavailable.
- Convert vague "build this well" instructions into acceptance criteria.
- Remove roadmap, product vision, or future ideas unless they constrain current
  code edits.
- Mark unknowns explicitly instead of inventing missing conventions.

## Candidate Shape

Use sections close to:

1. Scope
2. Repository Map
3. Commands
4. Working Rules
5. Validation
6. Context Maintenance

The result should be short enough to carry on every early coding task.
