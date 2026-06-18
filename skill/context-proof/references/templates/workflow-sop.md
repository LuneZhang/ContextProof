# Workflow SOP Template

Use this template for repeatable workflows such as release, deployment,
review, validation, incident, migration, or documentation update procedures.

## Optimization Goal

Turn workflow prose into an ordered, testable procedure that a coding agent can
follow without guessing.

## Keep

- Preconditions.
- Commands.
- Required files or paths.
- Approval gates.
- Expected outputs and rollback notes.

## Rewrite Strategy

- Put steps in execution order.
- Split preconditions, actions, validation, and handoff.
- Convert vague success language into observable checks.
- Keep negative constraints close to the risky step they govern.
- Remove background narrative that does not affect the procedure.

## Candidate Shape

Use sections close to:

1. Scope
2. Preconditions
3. Procedure
4. Validation
5. Safety Gates
6. Completion Report

Each step should be actionable or explicitly marked as a manual check.
