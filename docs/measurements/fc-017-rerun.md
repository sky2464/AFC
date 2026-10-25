# FC-017 slice 4 — live re-run (2026-10-25)

Run on a clean copy of `dev` at `71e6517` (FC-017 slices 1 to 3 built) with its own home and its own
code folder, in a headless session (`claude -p --resume`, Sonnet 5.5, default effort), driven through
the real flow with no extra instructions: `1` at the welcome, the goal (the PHP version checker, as
in FC-009), the folder, "Just me", "1" to start S-001, "Yes, keep it". Whole start plus first slice:
the slice was built, reviewed, shown and committed in 6 messages.

## Result: ceiling not met

| Run | Turns | Floor | Peak | Growth |
|---|---|---|---|---|
| FC-009 baseline, first live run | 41 | 64,312 | 101,048 | 36,736 |
| FC-009 re-run, `973da0c` | 28 | 65,582 | 111,592 | 46,010 |
| **FC-017 re-run, `71e6517`** | 32 | 74,721 | 116,637 | **41,916** |

Growth is 41,916 against a ceiling of 36,736, so it is not met. It is 9% below the FC-009 re-run
(46,010). The floor is 9k higher than before (more plugins and skill listings loaded on this Mac),
which is why growth, not peak, is judged.

| Part | FC-009 re-run | Needed (a third below) | FC-017 re-run | |
|---|---|---|---|---|
| Replies | 9,552 | 6,368 | 5,025 | met |
| Skill text | 11,371 | 7,581 | 9,483 | missed |
| Plan and spec edits | 6,004 | 4,003 | 4,573 | missed |
| Code and tests | 7,122 | | 9,856 | up |
| Files read | 5,481 | | 4,706 | |
| Other | 6,480 | | 8,273 | up |

## What to know before reading this as a verdict

- Replies fell by 47%. Skill text fell 17% and plan and spec edits 24%, both short of a third.
- The slice flow now does more than in the FC-009 re-run: FC-014's review ran before the slice was
  shown, and FC-015's changes are in the skill text. Code and tests (+2.7k) and other (+1.8k) grew
  with that work, so a like-for-like control (the same flow on `dev` before FC-017, made the same
  day) would show how much FC-017 itself saved. None was made; one run only.
- Earlier runs of the same flow spread by about 2.4k (44,274 to 46,689), so a single run is a rough
  reading.

## FC-019 slice 6 (build time and runs)

The first FC-017 build attempt failed on the gate, so
the whole-spec comparison with FC-015 is not clean. The clean part is slice 3: one builder, no
checker (not risky), the quick gate through `sh bin/afc gate`, one final full suite: 4 helpers,
about 295k tokens, 3.3 minutes. FC-015 slices 1 to 5 took 10 helpers and 45 minutes in total, about
9 minutes a slice, with a checker each. Time per non-risky slice is under half of FC-015's, and the
full suite ran once.
