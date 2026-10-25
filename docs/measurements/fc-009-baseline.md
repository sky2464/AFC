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

## Re-run result (2026-10-24): target not met

Run on a clean copy of `dev` at `973da0c` (FC-009 slices 1 to 3 built), with its own home and its own
code folder, in a headless session (`claude -p --resume`, Sonnet 5.5 at the default effort, the same
model as the baseline), driven through the real flow with no extra instructions: `1` at the welcome,
the goal, a folder, "just me", then "Yes" to start S-001 and "Yes, keep it" after the demo. It reached
the plan in four questions and finished with the slice committed.

| Run | Turns | Floor | Peak | Growth | Added fresh tokens |
|---|---|---|---|---|---|
| Baseline, first live run (2026-10-23) | 41 | 64,312 | 101,048 | 36,736 | 47,668 |
| Earlier run, before slices 2 and 3 (16:38) | 29 | 65,398 | 109,672 | 44,274 | 59,567 |
| Earlier run, before slices 2 and 3 (16:45) | 31 | 65,511 | 112,200 | 46,689 | 64,922 |
| **Re-run, dev `973da0c`** | 28 | 65,582 | 111,592 | **46,010** | 60,809 |

`compare` says growth went up 25% and the target is 24,490 or less, so `target_met` is false.

Two things stop this from being a plain pass or fail:

- **The two runs don't build the same thing.** The baseline's first slice was an app skeleton with no
  tests; since FC-003 the first slice is real and tested (here: a server, a page and 8 tests). That
  extra work is context, and it is meant to be there.
- **FC-009 itself moved the number by less than the noise.** The two earlier whole runs, made before
  slices 2 and 3 and building the same kind of slice, grew 44,274 and 46,689. The re-run's 46,010 sits
  inside that range, so the short rules and the skill split saved less than the difference between
  two runs of the same code. Their estimated saving is about 1k tokens of roughly 46k.

Where the re-run's growth went, roughly (each jump is credited to the tool call before it, so it also
holds the model's own reply): code and test files written about 9.5k, the model's replies about 9.5k,
skill text about 5.7k, plan and spec edits about 5.2k, files and rules read about 5.5k, and the rest
in turns that ran `afc` commands. The `afc` commands themselves printed only about 8,600 characters,
roughly 2k tokens, across 12 commands, so command output is not where the growth is.

One fix to the measuring: `compare` refused this run as "never got to commit the slice" although the
commit exists, because the session had set Flight Control's path in a variable (`A=…/bin/afc`, then
`sh $A deliver`), which is natural when the app and Flight Control are in different folders.
`token_usage.py` now follows a variable that the same command sets to a path ending in `bin/afc`, and
no other variable. The "hi" session and the runs that stopped early are still refused.
