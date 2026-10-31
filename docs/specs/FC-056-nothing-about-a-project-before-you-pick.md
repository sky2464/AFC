# FC-056 — Nothing about a project before you pick it

Size: M · Status: in progress · Started: 2026-10-28 · Done: - · Depends: FC-057
Area: flow

Found on 2026-10-28: a session opened with "check status" before the welcome's question was
answered, and the first reply described the active project (php-vuln-checker) in full: its goal,
last step and next step. The session-start hook hands Claude the active project's code folder,
workspace, last slice, active spec and brief path before the user has picked anything, and the
welcome itself shows the last slice.

## Goal

Until the user picks a project in a session, Flight Control says and reads nothing about it beyond
its name. The details arrive after the pick, from `sh bin/afc status`.

## Reaches the apps

Yes. The welcome, `status` and the start skill are shared; every user's sessions start this way.

## You'll know it works when

- A1. A new session's context line names the active project and the other projects only: no code
  folder, workspace, last slice, active spec or brief path. The welcome you see names the project
  to continue without its last slice.
- A2. After the pick, `sh bin/afc status` gives everything the context line used to: folders, last
  slice, active spec (`now`) and the brief path (`brief`), so slices start as before.
- A3. If the first message asks something else before the pick (for example "check status"), the
  reply names the project only and asks the welcome's question. The health-check line comes after
  the pick, not before.

## Out of scope

Maintenance-mode and undecided welcomes (they already set projects aside). The connector line's
project name. The `/afc` command's summary, which the user asks for.

## Assumptions to confirm

- [x] Nothing reads the project details from the context line except the first reply and the
  slice skill's brief path; `status` can carry them instead. Confirmed in slice 1–2: details live
  on `status` (`brief` included); `afc-slice` reads `brief` from there.

## Design notes

- `afc/hooks/session_start.py`: `_project_line` keeps the active name, other projects and paused
  ones; drops paths, last slice, active spec and brief. It adds the rule: before the pick, no
  `status`, `plan` or project files, and nothing about the project but its name. `_choices` drops
  `(last: …)` from the welcome.
- `afc/cli.py` `cmd_status`: add `brief` (the brief path) when the file exists.
- Skills: `afc-start` (Returning) says what to do before the pick; `afc-slice` takes the brief path
  from `status`. The health line says "once the user has answered the welcome's question".

## Slices

- [ ] 1. Only names before the pick — you'll see it by the session-start output for a project with
      a last slice and a brief: the context line and welcome hold its name only, and `status`
      returns the folders, last slice and `brief` (proves A1, A2)
- [ ] 2. The first reply waits for the pick — you'll see it by a new session opened with "check
      status": the reply names the project, asks the welcome's question, and the health line
      comes only after the answer (proves A3)

## Tasks

Slice 1:
- `afc/hooks/session_start.py`: `_project_line` and `_choices` as above.
- `afc/cli.py`: `brief` in `cmd_status`.
- `tests/test_welcome_pick.py`: context line and welcome hold no project details; `status` has them.

Slice 2:
- `afc/hooks/session_start.py`: health line timing; the before-the-pick rule.
- `.claude/skills/afc-start/SKILL.md`, `.claude/skills/afc-slice/SKILL.md`: wording.

## Decisions

## Shipped
