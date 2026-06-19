# Contributing

ContextProof treats coding-agent context as testable infrastructure. Contributions
should keep the project deterministic by default and avoid claiming behavioral
performance improvements without benchmark evidence.

## Development

Use Python 3.11 or newer.

```bash
python -m pip install -e .
python -m unittest discover -s tests
python -m contextproof.cli prepare-workflow . --deterministic
python scripts/acceptance_v06.py
```

## Pull Requests

- Keep the `skill/context-proof` folder portable.
- Keep `SKILL.md` concise and move detailed guidance into `references/`.
- Add tests for CLI behavior, schema changes, and scoring changes.
- Do not make static score changes without adding or updating fixtures.
- Do not add network calls to the default audit path.

## Evidence Policy

Static audit results are hygiene signals. Claims about agent performance require
recorded benchmark runs and should be represented in `benchmark_evidence`, not
inside the static score.
