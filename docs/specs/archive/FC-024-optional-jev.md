# FC-024 — Optional TypeSafe Jev (stub)

Size: S · Status: done · Started: 2026-10-25 · Done: 2026-10-25

## Goal

A place to plug TypeSafe Jev later without committing to product behavior now. Off by default; always off for enterprise; shadow-only when enabled; `TYPESAFE_API_KEY` from the environment; stdlib `urllib`; mockable tests; never overrides Flight Control hard blocks.

## You'll know it works when

- `afc/jev.py` exposes `evaluate(...)` that no-ops without a key and uses POST `https://api.typesafe.ai/v1/systemone` when a key and mock opener are supplied.
- `tests/test_jev.py` passes with no network.
- Workspace routing JSON includes `jev.enabled: false` by default.

## Out of scope

Calling Jev from review, scan, or hooks. Billing UI. Any dependency beyond stdlib.

## Slices

- [x] 1. Isolated adapter — you'll check it by `tests/test_jev.py`

## Decisions

- 2026-10-25: Ship adapter only; integration waits on owner priority.

## Shipped

Shipped 2026-10-25. Slices: 1.
