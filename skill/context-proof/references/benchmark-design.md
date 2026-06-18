# Benchmark Design

## Purpose

Benchmarking answers one question: did this context make an agent more effective
for real repository work?

Do not benchmark context by asking whether it sounds complete. Benchmark by
measuring task outcomes.

## Variants

Use explicit variants:

- `none`: no repository context file injected.
- `current`: the repository's current context files.
- `native-init`: a tool's default generated context from an `/init`-style flow.
- `contextproof-reviewed`: context after a human or agent reviews
  ContextProof findings and makes explicit changes.

Optional variants:

- `claude-init`
- `codex-init`
- `gemini-init`
- `full`
- `policy-only`

Native `/init` output is a baseline, not an oracle. It helps answer whether
ContextProof beats default tool behavior, but it does not define correctness.

## Task Selection

Choose tasks that represent normal repository work:

- A small bug fix.
- A test update.
- A feature that touches two or three files.
- A refactor with an existing validation command.
- A documentation-only change.

Separate existing-project scenarios from new-project scenarios. Existing
projects should measure context discovery and repository-specific validation.
New projects should measure whether generated context stays concise and avoids
invented conventions.

## Metrics

Collect these fields for each run:

- `task_id`
- `paired_group_id`
- `project_mode`
- `variant`
- `agent`
- `model`
- `repo_snapshot`
- `success`
- `tests_passed`
- `tokens_input`
- `tokens_output`
- `duration_seconds`
- `turns`
- `human_intervention`
- `files_read`
- `files_changed`
- `commands_run`
- `instruction_violations`
- `notes` optional

Legacy aliases `input_tokens`, `output_tokens`, and `files_touched` may be
accepted only when ingesting old data.

## Run Result Schema

Use JSONL, one run per line:

```json
{"task_id":"fix-login-timeout","project_mode":"existing_project","variant":"contextproof-reviewed","success":true,"tests_passed":true,"tokens_input":9800,"tokens_output":2900,"duration_seconds":620,"turns":5,"human_intervention":false,"files_read":18,"files_changed":5,"commands_run":2,"instruction_violations":0}
```

## Judgment Policy

Default benchmark judgment is metric-based. Do not use an LLM as the primary
judge for pass/fail. An LLM can annotate failures after deterministic metrics
are recorded.

## Optimizer Route Benchmarks

For optimizer prompt variants, record scenario routing fields in addition to
candidate comparison metrics:

- `classified_primary_scenario`
- `classified_secondary_scenarios`
- `selected_template`
- `classification_confidence`
- `classification_match` when a fixture defines an expected route

Judge prompt variants per scenario route as well as in aggregate. A prompt that
works well on token-heavy context but weakens safety-sensitive context should
not be treated as a universal improvement.

## Gold Candidate Evaluation

Built-in scenarios may include a curated reference candidate at:

```text
examples/scenarios/<scenario>/gold/AGENTS.gold.md
```

Use `evaluate-gold` to compare source vs candidate, source vs gold, and
candidate vs gold. Gold verdicts are deterministic test references, not
automatic answers for real user repositories.

For v0.5 optimizer prompt variants, a candidate is successful only when:

- `compare-context` does not regress.
- Score delta is non-negative.
- Critical/high findings do not increase.
- Token delta is non-positive, unless the gold reference also grows for a
  preservation reason and the candidate stays close to gold length.
- Gold verdict is `gold_aligned` or `partially_aligned`.
- Gold verdict is not `unsafe_regression`,
  `missing_required_preservation`, or `overcompressed`.

Benchmark rows should include:

- `gold_path`
- `gold_alignment_verdict`
- `gold_alignment_score`
- `missing_gold_preservation`
- `extra_candidate_findings_vs_gold`
- `overcompression_flags`

Summaries should include per-variant and per-scenario-route gold alignment
rate, unsafe regression count, overcompression count, and missing preservation
count.
