# Security

ContextProof scans coding-agent instruction files and may execute local Python
scripts from this repository. Review third-party forks and skill bundles before
installing them.

## Reporting

Please report security issues through GitHub Security Advisories when available.
If advisories are unavailable, open a private communication channel with the
maintainer before publishing details.

## Scope

Security-sensitive areas include:

- risky shell patterns in generated or recommended context
- prompt-injection-like instructions in agent context files
- unintended file overwrite behavior
- network calls or external execution added to deterministic audit paths

The default v0.1 audit path should remain local and deterministic.
