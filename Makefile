.PHONY: test audit minimize benchmark

test:
	python -m unittest discover -s tests

audit:
	python -m contextproof.cli audit . --pr-comment --minimize

minimize:
	python -m contextproof.cli minimize . --output .contextproof/context.min.md

benchmark:
	python -m contextproof.cli summarize-runs examples/benchmark-runs.jsonl --md-out .contextproof/benchmark-summary.md
