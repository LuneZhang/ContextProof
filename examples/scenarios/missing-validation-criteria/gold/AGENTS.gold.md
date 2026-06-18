# AGENTS.md

## Scope

These instructions apply to payment and billing changes.

## Working Rules

- Keep changes scoped to the requested task.
- Review payment code in `src/payments` when the task touches payment behavior.
- Review billing jobs in `jobs/billing.py` when the task touches recurring billing.

## Validation

- Run the most relevant available test command for payment or billing changes.
- If no validation command exists in the repository, report that gap and describe the manual checks performed.
