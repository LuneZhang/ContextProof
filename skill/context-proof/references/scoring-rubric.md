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

## Interpretation

- 90-100: lean and actionable.
- 75-89: usable, with some cleanup needed.
- 60-74: likely to waste context or create inconsistent behavior.
- Below 60: do not use as CI-approved agent context without revision.

Reports must label this as a static hygiene score. Behavioral claims require
benchmark evidence.
