# Scoring Rubric

ContextProof's static score is a deterministic hygiene score from 0 to 100. It
is not a claim that agent performance will improve by the same amount.

## Dimensions

Starting weights:

- Discoverability: 10
- Actionability: 20
- Minimality: 15
- Consistency: 20
- Safety: 20
- Workflow fit: 15

Findings subtract weighted penalties from one or more dimensions:

```text
dimension_score = max(0, dimension_weight - sum(severity_penalty * confidence_multiplier * finding_dimension_share))
dimension_percent = round(100 * dimension_score / dimension_weight)
total = round(sum(dimension_score))
```

## Severity Penalties

- Critical: 12
- High: 8
- Medium: 4
- Low: 2
- Info: 0

Confidence multipliers:

- High: 1.0
- Medium: 0.75
- Low: 0.5

Critical safety findings cap the total score at 69 unless a future release can
explicitly mark the finding as non-exploitable.

## Calibration

Scoring changes must be checked with:

```bash
python scripts/contextproof.py calibrate-scorer examples/calibration/cases.jsonl
```

Calibration cases declare expected issue ids, severity, scoring dimensions, and
score buckets. The report must list missing expected issues, unexpected issues,
severity mismatches, dimension mismatches, score bucket mismatches, and failed
cases.

Do not add broad Markdown style rules to improve calibration numbers. Add or
adjust deterministic rules only when they affect agent-facing context quality or
candidate evaluation.

## Validation Gap Policy

An explicit instruction to report a missing validation command and describe
manual checks can satisfy actionability for repositories where no test, lint,
typecheck, build, make, or just command exists. This is not a substitute for a
runnable command when one is available.

## Interpretation

- 90-100: lean and actionable.
- 75-89: usable, with some cleanup needed.
- 60-74: likely to waste context or create inconsistent behavior.
- Below 60: do not use as CI-approved agent context without revision.

Reports must label this as a static hygiene score. Behavioral claims require
benchmark evidence.
