# FC-043 — Ready means ready

Size: M · Status: in progress · Started: 2026-10-26 · Done: -

Found on 2026-10-26, comparing this plan with AgToosa's. "Ready for build" is the gate for the rule
*spec, then slices, then tasks, then queue*, but it checks almost nothing:

- `_ready` in `afc/cli_plan.py` only asks whether "Reaches the apps" has text, and only for Flight
  Control's own plan. A project's `S-` specs get no answer at all (php-vuln-checker's S-002 and S-003
  show nothing).
- Since FC-030 and FC-042 the bullets under "You'll know it works when" are matched to tests only with
  `--tests`, so by default nothing links a criterion to the slice that proves it. A criterion can be
  forgotten and the spec still finishes.
- The template every app gets has no Tasks section, although every recent FC spec has one, and
  "Shipped" is one line ("Shipped 2026-10-26. Slices: 3.") while the real results sit in Decisions.
- FC-041 builds on "we expect… slice 1 confirms" and has no place to keep such guesses until they
  are settled.

## Goal

`afc plan` says, for every spec in Next, in Flight Control's plan and in a project's, whether it is
ready for build and, when it is not, what is missing in plain words. A criterion with no slice behind
it is caught before the build, without any test. Guesses a spec rests on are listed, not hidden.

## Reaches the apps

Yes. The same plan tool and the same spec template serve every user's project, so a user's `S-`
specs get the same honest answer, new specs start with numbered criteria, Tasks and Assumptions, and a
criterion nobody builds can no longer slip through when the user asked for no tests
(`afc/plan.py`, `afc/cli_plan.py`, `templates/workspace/spec.md`, `.claude/skills/afc-slice/SKILL.md`).

## You'll know it works when

- A1. `sh bin/afc plan` on a scratch project with a bare spec in Next shows `ready: false` and a
  `missing` list in plain words (goal, criteria, out of scope, slices, tasks); the same spec filled in
  shows `ready: true`. Project specs answer too. Flight Control's own specs still need "Reaches the
  apps".
- A2. Criteria may be numbered (`A1.`, `A2.`) and a slice may end with `(proves A1, A2)`. A numbered
  criterion no slice names shows "A3 has no slice that proves it", and a slice naming a criterion that
  does not exist shows that. Older specs with unnumbered criteria are not blocked: `plan` adds one
  note that their criteria are not linked to slices.
- A3. A spec with an unticked assumption shows it under `to_confirm`, and `afc-slice` says: settle the
  open assumptions in the first slice before building further.
- A4. A spec made by `plan add` has Assumptions to confirm, a numbered criterion example, `(proves
  A1)` on its slice example and a Tasks section.
- A5. `plan done` writes the Shipped line with the date, the slices and "Criteria: n of n proven"
  (or "not numbered").
- A6. On a scratch copy of php-vuln-checker's plan, S-002 and S-003 now answer; on Flight Control's
  own plan, FC-044 (numbered criteria, `proves` on every slice) shows `ready: true` with no
  `missing` and no note.

## Out of scope

Judging whether a slice really proves its criterion (that stays with the review and the user's eyes).
Rewriting older specs to the new shape. Any test.

## Design notes

- Helpers in `afc/plan.py`: `criteria(spec_text)` reads bullets under "You'll know it works when"
  that start `A<n>.`; `proofs(label)` reads `(proves …)` at the end of a slice; `assumptions(spec_text)`
  reads checkbox lines under "Assumptions to confirm"; `readiness(spec_text, fc)` returns
  `{ready, missing, notes, to_confirm}`. `_ready` calls it; `missing`, `notes` and `to_confirm` appear
  in the output only when not empty, to keep the reply small.
- `(proves …)` sits after "— you'll see it by", so `ship.changelog_entry` already drops it from the
  changelog. `review.acceptance_lines` still reads the bullets (an `A1.` prefix does not hurt its word
  match, and it runs only with `--tests`).
- "Tasks" counts as filled when each slice has a `Slice n:` line, the shape FC-042 uses.
- Plain messages, e.g. "no slices yet", "slice 2 has no 'you'll see it by'". No jargon.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Say what is missing — you'll see it by a scratch project plan with a bare spec in Next giving
      `ready: false` and the list, the filled-in spec giving `ready: true`, and an `S-` spec answering
      too (proves A1)
- [x] 2. Criteria tied to slices — you'll see it by a scratch spec whose A3 has no slice and whose
      slice 2 names A9 giving both messages, and an older unnumbered spec giving only the note
      (proves A2)
- [x] 3. Assumptions — you'll see it by a scratch spec with one open assumption showing it under
      `to_confirm`, and `afc-slice` carrying the sentence about settling it in slice 1 (proves A3)
- [x] 4. New specs and Shipped — you'll see it by `plan add` on a scratch plan giving a spec with the new
      sections, and `plan done` on it writing the Shipped line (proves A4, A5)
- [x] 5. Live on both plans — you'll see it by `sh bin/afc plan` on Flight Control's own plan and on a
      scratch copy of php-vuln-checker's plan (own registry and workspace) showing the answers in A6
      (proves A6)

## Tasks

Slice 1:
- `afc/plan.py`: `readiness(spec_text, fc)` checks Goal, Out of scope, criteria, slices (each with
  "you'll see it by"), Tasks per slice, and "Reaches the apps" when `fc`.
- `afc/cli_plan.py`: `_ready` returns `readiness` for every plan, not only FC's.

Slice 2:
- `afc/plan.py`: `criteria`, `proofs`; coverage both ways inside `readiness`.

Slice 3:
- `afc/plan.py`: `assumptions`; `to_confirm` in `readiness`.
- `.claude/skills/afc-slice/SKILL.md`: one sentence.

Slice 4:
- `templates/workspace/spec.md`: Assumptions to confirm, `A1.` example, `(proves A1)`, Tasks.
- `afc/cli_plan.py` `cmd_done`: write the Shipped line.

Slice 5:
- Copy php-vuln-checker's plan into a scratch workspace, run `plan`, write the result in Decisions.
  Never use the real project.

## Decisions

- Slice 5, run 2026-10-26 on a scratch copy of php-vuln-checker's plan (own registry and workspace via
  `AFC_HOME`, never the real project; the copy matched the real plan file for file):
  - S-002 and S-003 now answer. Both show `ready: false`, `missing: ["no slices yet"]` and one note:
    "the criteria are not numbered, so they are not linked to slices". Before this spec they showed
    nothing. They are older specs, so the note does not block them; they only lack slices.
  - Flight Control's own plan: FC-044 and FC-045 both show `ready: true` with no `missing` and no
    `notes` (A6).

## Shipped
