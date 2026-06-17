# Team Agent Context Demo

This fixture mimics a team-maintained agent context that accumulated rules over
time. It is intentionally flawed, but the issues are closer to real repository
drift than the obvious bad-context demo.

Run:

```bash
python -m contextproof.cli audit examples/team-agent-context --pr-comment
```

Expected static findings include:

- vague quality requirements
- over-broad repository exploration
- duplicated rules across agent surfaces
- missing concrete validation commands
- a high density of absolute instructions

