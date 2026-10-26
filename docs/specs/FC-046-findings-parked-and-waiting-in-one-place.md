# FC-046 — Findings, parked and waiting in one place

Size: M · Status: next · Started: - · Done: -

Found on 2026-10-26, comparing this plan with AgToosa's, whose roadmap index says every item must end
as shipped, a manual task, a backlog spec, or an explicit parked or rejected decision.

- 47 findings (21 + 10 + 9 + 7) sit in five tables inside `docs/master-plan.md`, about 80 of its 225
  lines. None has a State, so nobody can see which are still open. The project template has no such
  sections, although the plan says it is "the same shape it gives every project".
- Intake has lapsed: the tables stop on 2026-10-25, while FC-036 to FC-042 came from newer reviews
  and are recorded only inside their specs ("Found on…").
- Things waiting on the user are tracked nowhere: R6 (A-FC-test sits on old code) and FC-040's merge,
  tag and publish steps.
- A spec that is put aside by `plan drop` is filed in Done as "(dropped)", so ideas vanish into the
  finished list with no reason and no "revisit when".
- Most of the 43 specs answer a live-run problem. Nothing says where Flight Control is headed.
- Even with a State column, the state would drift by hand: nothing links a finding to the spec that
  fixes it, so someone has to remember to flip it, which is how the tables went stale.
- Not the same as `afc index findings`, which lists review results for projects.

## Goal

One findings file with a State for every item, a "Waiting on you" list and a "Parked" list (with a
reason and when to look again) in every plan, one command to take a finding in, states that follow the
specs on their own, and a few Areas that say where the work is going, each with a target.

## Reaches the apps

Yes. Every project plan gets the same Waiting-on-you and Parked sections, so a user's "later" ideas and
the steps only they can do stop living in the conversation, and `plan find` lets Claude note a problem
the moment it is seen (`afc/plan.py`, `afc/cli_plan.py`, `templates/workspace/plan/master-plan.md`,
a new `templates/workspace/plan/findings.md`).

## You'll know it works when

- A1. `docs/findings.md` holds all 47 findings under their existing IDs, each with a State (open,
  fixed in FC-0xx and the release, waiting on you, parked, or no change needed); the master plan keeps
  one line with the count still open.
- A2. `sh bin/afc plan find "<text>"` adds a finding with the next ID (`F-001`, `F-002`, …) in State
  open and logs it; the same command works on a scratch project.
- A3. `plan park <id> --why "<reason>" --revisit "<when>"` takes a waiting spec out of Next into
  Parked; `plan unpark <id>` brings it back; `plan drop` no longer files an idea in Done.
- A4. `plan wait "<step>"` adds a row to Waiting on you and `plan wait --done <n>` clears it; R6 and the
  FC-040 release steps are in it.
- A5. `sh bin/afc check` says when a finding has no State, or says "fixed in FC-0xx" for a spec that is
  not Done.
- A7. A spec says which findings it fixes in one header line (`Fixes: R7, F-003`). `plan start` moves
  those findings to "in progress", `plan done` moves them to "fixed in FC-0xx" with the release when
  there is one, and `plan drop` or `park` puts them back to open. Nobody edits a State by hand.
- A8. `sh bin/afc plan` shows one line, "Findings: n open, n in progress, n waiting", and names open
  findings that no queued spec fixes ("unplanned"), so nothing sits open with nobody on it.
- A9. Each finding records where it was found (a session, a review or a date) in a Found column, and
  the 47 old ones are backfilled from the headings they sit under now.
- A6. The plan has `## Areas`: four rows (flow, tokens, safety, updates), each with a target and the
  Scoreboard number it is judged by (FC-045), and each Next spec names its area in its first line.

## Out of scope

Syncing findings to GitHub issues. Reviewing the 47 old findings again: this spec only gives them a
State. Rewriting specs to add an area (only the ones in Next).

## Design notes

- Old IDs stay (1–21, M1–M10, U1–U9, R1–R7); new ones are `F-nnn` so nothing collides.
- States: open, in progress, fixed, waiting on you, parked, no change needed. Only the first three are
  moved by the tool (A7); the rest are set when the finding is taken in or by `plan park` and
  `plan wait`.
- `Fixes:` is read from the spec's first block of header lines, like Size and Status. An ID it names
  that is not in the findings file stops `plan start` with one plain sentence, so a typo cannot fix
  nothing silently.
- Why not a link table: the spec is the one place a builder always reads, so the link lives there and
  the findings file only mirrors it.
- Waiting on you and Parked are plain tables; the code reads them with `read_rows`, appended after Next
  so existing section order is unchanged.
- Fixed-in checks read the Done rows and archive index; they do not open specs.
- Areas need the Scoreboard from FC-045; do slice 5 after FC-045 is done.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Findings leave the plan — you'll see it by `docs/findings.md` holding the 47 with their State
      and `docs/master-plan.md` shrinking by about 80 lines (proves A1)
- [ ] 2. Take a finding in with one command — you'll see it by `plan find` on Flight Control's plan and a
      scratch project (proves A2)
- [ ] 3. Parked and waiting — you'll see it by a scratch spec parked and brought back, a drop no longer
      landing in Done, and R6 and the FC-040 steps in Waiting on you (proves A3, A4)
- [ ] 4. The check — you'll see it by a scratch findings file with one stateless finding and one false
      "fixed in" giving both sentences in `check` (proves A5)
- [ ] 5. Findings close themselves — you'll see it by a scratch spec with `Fixes: F-001` moving the
      finding to in progress on `plan start` and to fixed on `plan done`, `plan` showing the
      one-line count and the unplanned ones, and a typo ID refused (proves A7, A8, A9)
- [ ] 6. Areas — you'll see it by the four rows with their Scoreboard numbers and the Next specs naming
      their area (proves A6)

## Tasks

Slice 1:
- `docs/findings.md` (new) from the five tables; remove them from `docs/master-plan.md`.

Slice 2:
- `afc/cli_plan.py`: `find`; `templates/workspace/plan/findings.md`.

Slice 3:
- `afc/cli_plan.py`: `park`, `unpark`, `wait`; `cmd_drop` stops writing to Done; both sections in
  `templates/workspace/plan/master-plan.md`.

Slice 4:
- `afc/cli_health.py`: `finding_no_state`, `finding_fixed_not_done`.

Slice 5:
- `afc/plan.py`: read `Fixes:`; `afc/cli_plan.py` `cmd_start`, `cmd_done`, `cmd_drop`, `cmd_park` set
  the finding states; `cmd_plan` adds the count and the unplanned list.
- Backfill the Found column of the 47 findings in `docs/findings.md`.

Slice 6:
- `docs/master-plan.md`: `## Areas`.

## Decisions

## Shipped
