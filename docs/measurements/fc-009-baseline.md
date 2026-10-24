# FC-009 baseline: first live run

Measured 2026-10-24 with `python3 docs/measurements/token_usage.py` on the session transcript of the
first live run (project start plus the first slice, php-vuln-checker, 2026-10-23 22:48 to 22:57):
`~/.claude/projects/-Users-chicademy-Documents-Code-A-FC-test/96aa029b-9a1b-4b46-928d-2d9613abb61b.jsonl`.

| Number | Value |
|---|---|
| Turns | 41 |
| Peak context (biggest single prompt) | 101,048 |
| Fresh tokens (input + cache creation + output) | 79,767 |
| Cache-read tokens (summed) | 3,225,232 |

The peak context matches finding 14 ("about 101k tokens"). Slice 4 repeats this measurement on a
re-run and compares the same numbers; "at least a third fewer" means peak context at or below
67,365 and fresh tokens at or below 53,178.
