# FC-023 — Token usage by model and role

Size: S · Status: next · Started: - · Done: -

Asked for on 2026-10-25, to see which models and role helpers spend tokens during spec builds and
project slices, using the same transcripts FC-017 and FC-018 already measure.

## Goal

`docs/measurements/token_usage.py` reports token totals broken down by model and by role (main
session vs named helpers), with an optional rough cost column from a small built-in price table.

## You'll know it works when

- `python3 docs/measurements/token_usage.py --by-model <transcript.jsonl>` prints one line per model
  with input, cache read, cache creation, output and total fresh tokens, summed with the same
  per-message-id deduping as today.
- `python3 docs/measurements/token_usage.py --by-role <transcript.jsonl>` attributes turns to
  `main`, `afc-research`, `afc-plan`, `afc-build`, `afc-check`, `afc-builder`, `afc-checker` or
  `unknown`, using agent name metadata from the transcript when present and falling back to
  `unknown` without crashing.
- `python3 docs/measurements/token_usage.py --cost <transcript.jsonl>` adds estimated USD per model
  from a documented table in the script header (editable constants, not live pricing APIs); missing
  models list as `no_price` and still show tokens.
- Existing flags (`--parts`, two-file compare, whole start plus first slice guard) behave as before;
  tests lock current output for a small fixture transcript.
- README or script docstring states that cost is approximate and for comparisons only.

## Out of scope

Billing integration, live price feeds, or shipping the script in `bin/afc`. Changing growth or
floor definitions. Dashboards or Cursor panel plugins.

## Design notes

- **Transcript fields.** Prefer `message.model` and subagent / workflow labels already in JSONL; map
  legacy builder/checker names to roles for FC-018 workflows.
- **Deduping.** Reuse `measure()`'s message-id logic so extended reports do not double-count
  retried turns.
- **Cost table.** Static USD per million tokens for a few Anthropic models; Bedrock/Vertex IDs match
  by suffix or explicit map entry.
- **Output.** Plain text tables to stdout for easy paste into `docs/measurements/`; optional
  `--json` for automation in one slice if cheap.

## Slices

- [ ] 1. Fixture and regression — you'll check it by `tests/test_token_usage.py` (or under
      `docs/measurements/`) locking today's single-file summary on a checked-in minimal JSONL (tests)
- [ ] 2. `--by-model` — you'll check it by the same fixture producing two models with correct sums
      (tests)
- [ ] 3. `--by-role` — you'll check it by a fixture with labeled helper turns mapping to `afc-build`
      and `main` (tests)
- [ ] 4. `--cost` — you'll check it by known models producing a positive USD estimate and an unknown
      model listing `no_price` (tests)

## Decisions

- 2026-10-25: Measurement stays in `docs/measurements/` only, not shipped product.

## Shipped
