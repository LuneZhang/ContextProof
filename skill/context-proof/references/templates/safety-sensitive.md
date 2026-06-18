# Safety-Sensitive Context Template

Use this template when context mentions production, databases, migrations,
secrets, credentials, deploys, deletes, destructive shell commands, or broad
automation permissions.

## Optimization Goal

Preserve productive guidance while making dangerous operations hard to perform
accidentally.

## Keep

- Explicit approval requirements.
- Production, secret, database, migration, deploy, and deletion boundaries.
- Validation commands and rollback checks.
- Safe alternatives for risky commands.

## Rewrite Strategy

- Replace unsafe shortcuts with safe default procedures.
- Put destructive operations behind explicit user confirmation.
- Ban secret exfiltration and blind `.env` reads.
- Require dry runs, backups, or scoped commands where relevant.
- Avoid excessive "never" lists that drown out the real safety gates.
- Keep safety rules concrete enough that a user can detect violations.

## Candidate Shape

Use sections close to:

1. Scope
2. Safe Defaults
3. Restricted Operations
4. Approval Gates
5. Commands And Validation
6. Incident Or Rollback Notes

Do not make dangerous shell patterns easier to copy.
