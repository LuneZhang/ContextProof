# Bad Agent Context Demo

This fixture intentionally contains flawed coding-agent instructions.

Run:

```bash
python -m contextproof.cli audit examples/bad-agent-context --pr-comment
```

Expected static findings include:

- vague quality rules
- over-broad repository exploration
- risky shell text
- conflicting ask-before-editing guidance

The generated report files appear under:

```text
examples/bad-agent-context/.contextproof/
```

Do not overwrite the fixture unless you are intentionally updating the demo.
