# FC-025 — Token usage cost by model

Size: S · Status: done · Started: 2026-10-25 · Done: 2026-10-25

## Goal

The measurement script can estimate run cost from transcript models, so role and model experiments can be compared in dollars as well as tokens.

## You'll know it works when

- `docs/measurements/token_usage.py` adds `estimated_cost_usd` and `tokens_by_model_key` to `measure()` when assistant lines include `model`.
- `tests/test_token_usage.py` covers a Haiku line with a positive cost estimate.

## Slices

- [x] 1. Cost fields — you'll check it by `tests/test_token_usage.py` (`test_estimates_cost_when_model_present`)

## Decisions

- 2026-10-25: Prices are rough USD/Mtok hints for comparison, not an invoice.

## Shipped

Shipped 2026-10-25. Slices: 1.
