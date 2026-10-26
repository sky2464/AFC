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
- Not the same as `afc index findings`, which lists review results for projects.

## Goal

One findings file with a State for every item, a "Waiting on you" list and a "Parked" list (with a
reason and when to look again) in every plan, one command to take a finding in, and a few Areas that
say where the work is going, each with a target.

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
- A6. The plan has `## Areas`: four rows (flow, tokens, safety, updates), each with a target and the
  Scoreboard number it is judged by (FC-045), and each Next spec names its area in its first line.

## Out of scope

Syncing findings to GitHub issues. Reviewing the 47 old findings again: this spec only gives them a
State. Rewriting specs to add an area (only the ones in Next).

## Design notes

- Old IDs stay (1–21, M1–M10, U1–U9, R1–R7); new ones are `F-nnn` so nothing collides.
- Waiting on you and Parked are plain tables; the code reads them with `read_rows`, appended after Next
  so existing section order is unchanged.
- Fixed-in checks read the Done rows and archive index; they do not open specs.
- Areas need the Scoreboard from FC-045; do slice 5 after FC-045 is done.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [ ] 1. Findings leave the plan — you'll see it by `docs/findings.md` holding the 47 with their State
      and `docs/master-plan.md` shrinking by about 80 lines (proves A1)
- [ ] 2. Take a finding in with one command — you'll see it by `plan find` on Flight Control's plan and a
      scratch project (proves A2)
- [ ] 3. Parked and waiting — you'll see it by a scratch spec parked and brought back, a drop no longer
      landing in Done, and R6 and the FC-040 steps in Waiting on you (proves A3, A4)
- [ ] 4. The check — you'll see it by a scratch findings file with one stateless finding and one false
      "fixed in" giving both sentences in `check` (proves A5)
- [ ] 5. Areas — you'll see it by the four rows with their Scoreboard numbers and the Next specs naming
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
- `docs/master-plan.md`: `## Areas`.

## Decisions

## Shipped
