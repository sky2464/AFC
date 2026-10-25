# FC-009 baseline: first live run

Measured 2026-10-24 with `python3 docs/measurements/token_usage.py` on the session transcript of the
first live run (project start plus the first slice, php-vuln-checker, 2026-10-23 22:48 to 22:57):
`~/.claude/projects/-Users-chicademy-Documents-Code-A-FC-test/96aa029b-9a1b-4b46-928d-2d9613abb61b.jsonl`.

| Number | Value |
|---|---|
| Turns | 41 |
| Peak context (biggest single prompt) | 101,048 |
| Floor (the first turn's prompt, before anything happened) | 64,312 |
| Growth (peak minus floor) | 36,736 |
| Fresh tokens (input + cache creation + output) | 79,767 |
| Fresh tokens added after the first turn | 47,668 |
| Cache-read tokens (summed) | 3,225,232 |

The peak context matches finding 14 ("about 101k tokens"). The floor is the system prompt, tool
definitions and the plugin and skill listings that load before Flight Control does anything, so it
is mostly outside this repo. That is why slice 4 judges growth, not the peak: "at least a third
fewer" would otherwise mean a peak of 67,365, only about 3k above the floor. The target is growth
of 24,490 or less (a third under 36,736), compared with each run's floor shown beside it.

## Re-run

Do the same start and first slice again on a copy of `dev` with its own home (`CONTRIBUTING.md`,
"Set up"), then compare:

```
python3 docs/measurements/token_usage.py <baseline.jsonl> <rerun.jsonl>
```

The re-run's transcript is under `~/.claude/projects/` in the folder named for where `claude` was
started. `target_met` is true when growth is 24,490 or less.

Both runs must be a whole start plus first slice: the transcript has to show `afc new`, `afc scan`
and `afc deliver` run through the Bash tool. Anything shorter is refused with a plain error naming
the steps it never reached. This exists because the newest transcript in that folder was once a
two-turn "hi" session, and it passed as a 95% saving. Naming the transcript instead of using the
newest one avoids the same mistake.
