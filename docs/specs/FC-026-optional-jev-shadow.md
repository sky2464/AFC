# FC-026 — Optional Jev shadow

Size: S · Status: next · Started: - · Done: -

Asked for on 2026-10-25, to try TypeSafe Jev classification on guard events in shadow mode without
changing allow/deny behaviour unless explicitly enabled later.

## Goal

When `TYPESAFE_API_KEY` is set and shadow mode is on, Flight Control sends a subset of pretool guard
context to TypeSafe Jev, logs the verdict, and always applies the existing local guard outcome.
Enterprise profiles force shadow off. Implementation uses only stdlib `urllib`; tests mock the HTTP
layer.

## You'll know it works when

- Shadow is off by default: no HTTP call without `AFC_JEV_SHADOW=1` (or documented env name) and
  `TYPESAFE_API_KEY`.
- Enterprise profile (`afc-profile` enterprise) sets shadow off regardless of env; a test proves the
  client is never constructed.
- When shadow is on and the key is set, pretool (or one documented hook) posts a JSON payload and
  records request id, label and suggested action in a log under the workspace (not the app repo),
  without changing the hook's allow/deny result.
- Network code lives in one small module using `urllib.request`; no third-party HTTP dependency.
- `tests/test_jev_shadow.py` mocks `urllib` and asserts: no call when off, call when on, local
  outcome unchanged when Jev says block, enterprise never calls.
- Missing key with shadow on: one-line log and no raise; session continues.

## Out of scope

Enforcing Jev verdicts over local guards. Storing API keys in files (env only). UI for Jev results.
Non-enterprise production reliance on Jev. Shipping TypeSafe SDK as a dependency.

## Design notes

- **Payload.** Minimal fields: tool name, path summary, maintenance flag, project id — no secrets, no
  full file contents; align with TypeSafe docs when implementing.
- **Timeout.** Short connect/read timeout (e.g. 2s) so shadow never blocks the hook noticeably.
- **Log rotation.** Append-only log with size cap or single file per day; detail in slice 2.
- **Feature flag.** `AFC_JEV_SHADOW` defaults false; document beside secrets in env setup skill.

## Slices

- [ ] 1. Client module — you'll check it by `tests/test_jev_shadow.py` mocking urllib: POST shape,
      timeout, no-op without key (tests)
- [ ] 2. Pretool integration — you'll check it by hook tests: shadow on logs verdict, return value
      matches pre-Jev guard; enterprise profile skips call (tests)
- [ ] 3. Docs and env — you'll check it by a content test or CONTRIBUTING note listing env vars and
      enterprise always-off rule

## Decisions

- 2026-10-25: Shadow only; local guard remains authoritative.

## Shipped
