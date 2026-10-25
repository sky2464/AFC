# FC-020 slice 5 — live re-run (2026-10-25)

Same method as `fc-017-rerun.md`: a clean copy of `dev` at `4087be3` (FC-020 slices 1 to 4 built)
with its own home and code folder, a headless session (`claude -p --resume`, Sonnet 5.5, default
effort), the real flow with no extra instructions: `1` at the welcome, the goal (PHP version
checker), the folder, "Just me", "1" to start the first step, "Yes, keep it". The slice was built,
reviewed, shown and committed in 6 messages.

The control is the FC-017 re-run made earlier the same day on `dev` at `71e6517`
(`fc-017-rerun.md`), the same flow before FC-020. No second control was run.

## Result: all three targets met

| Run | Turns | Floor | Peak | Growth |
|---|---|---|---|---|
| FC-017 re-run (control), `71e6517` | 32 | 74,721 | 116,637 | 41,916 |
| **FC-020 re-run, `4087be3`** | 34 | 74,720 | 106,513 | **31,793** |

Growth 31,793 is at most the 36,736 ceiling, and 24% below the control.

| Part | Control | FC-020 re-run | Target |
|---|---|---|---|
| Skill text | 9,483 | 6,394 | at most 7,581: met |
| Plan and spec edits | 4,573 | 0 | at most 4,003: met, see below |
| Replies | 5,025 | 4,356 | |
| Code and tests | 9,856 | 6,859 | |
| Files read | 4,706 | 2,632 | |
| Other | 8,273 | 11,552 | |

## Read this before trusting the plan-and-spec figure

Plan and spec edits shows 0 because the script counts Edit and Write calls on those files, and
`sh bin/afc slice record` is a Bash command, so its cost lands under Other (+3.3k). The honest
comparison is plan and spec edits plus Other: 12,846 in the control, 11,552 now, 10% lower. The
bookkeeping was done: the run wrote the `decisions.md` entry for the slice.

## Caveats

- One run each; runs of the same flow spread by about 2.4k.
- The new run's session said "Flight Control's own health check reported 28 problems" in two replies.
  The copy sits in a scratch folder, so those are likely about the copy and not the real checkout;
  it was not looked into.
- The control ran on a code folder that built 19 tests, this one built 6, so code and tests (-3.0k)
  is not comparable. Part of the 10k total drop is that smaller slice.
