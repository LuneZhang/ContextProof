# Optimization Checklist

Use this checklist before recommending an optimized context candidate.

## Source Understanding

- [ ] Confirm the file is agent-facing context.
- [ ] Identify the agent surface: Codex, Claude Code, OpenCode, Cursor,
  Windsurf, Pi, Copilot, MCP, or generic.
- [ ] Identify whether this is an existing project, new-project `/init` brief,
  or migration between agent surfaces.
- [ ] Read the ContextProof findings before editing.
- [ ] Run or inspect `route-optimizer` output before drafting.
- [ ] Read the selected scenario template under `references/templates/`.

## Preservation

- [ ] Keep explicit validation commands.
- [ ] Keep repository-specific paths and command names.
- [ ] Keep safety boundaries and approval requirements.
- [ ] Keep instructions that prevent known repeated mistakes.
- [ ] Keep agent-specific loader conventions when they matter.

## Reduction

- [ ] Remove generic quality advice that cannot be tested.
- [ ] Replace broad exploration mandates with task-scoped discovery.
- [ ] Deduplicate repeated rules.
- [ ] Resolve contradictory rules.
- [ ] Compress long directory maps unless they are essential.
- [ ] Move conditional details into referenced docs when possible.

## Candidate Safety

- [ ] Write only to `.contextproof/candidates/` unless the user asked otherwise.
- [ ] Do not overwrite source context files.
- [ ] Include a short rationale.
- [ ] List unresolved risks.
- [ ] Run `compare-context` and inspect regression flags.
- [ ] For included scenario fixtures, run `evaluate-gold` and inspect the gold
  alignment verdict.
- [ ] Report the selected classification route and template.

## Accept Candidate Only If

- [ ] Static score improves or remains acceptable.
- [ ] Critical/high findings decrease or do not increase.
- [ ] Token estimate decreases or the added text is justified.
- [ ] Validation commands are preserved.
- [ ] No new risky shell or safety findings are introduced.
- [ ] Gold verdict is `gold_aligned` or `partially_aligned` when a gold
  reference exists.
- [ ] Any removed project-specific paths are intentionally removed and noted.
