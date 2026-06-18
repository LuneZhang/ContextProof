# Token-Heavy Context Template

Use this template when the main problem is oversized, repetitive, or
low-density persistent agent context.

## Optimization Goal

Reduce token cost while preserving the few facts and rules that materially
improve coding-agent behavior.

## Keep

- Commands.
- Important paths.
- Safety boundaries.
- Architecture facts that affect normal edits.
- Known recurring mistakes that the context prevents.

## Rewrite Strategy

- Delete repeated rules after keeping the clearest version.
- Replace long directory maps with the paths an agent normally needs.
- Move rare or conditional details into referenced docs instead of top-level
  context.
- Remove product vision, roadmap, meeting notes, and generic advice.
- Prefer compact lists over paragraphs when the content is operational.
- Preserve enough path and command anchors for `compare-context` to pass.

## Candidate Shape

Use sections close to:

1. Scope
2. Essential Paths
3. Commands
4. High-Value Rules
5. Safety Boundaries
6. Links To Conditional Detail

The result should be meaningfully shorter. Brevity is not acceptable if it
deletes validation commands or important project constraints.
