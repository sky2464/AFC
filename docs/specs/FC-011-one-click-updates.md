# FC-011 — One-click updates

Size: L · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-24.

## Goal

Someone on an older Flight Control hears about a newer release on their own, says yes once, and is
on the latest version, without knowing git. Today the only way is to run `git pull` by hand in the
`A-FC` folder (README), and Flight Control doesn't know which version it is.

## You'll know it works when

- When a session starts and a newer release exists, then the welcome says so in one line
  (`Flight Control v0.02a is out; you have v0.01a.`) and offers: 1. Update now (recommended)
  2. Not now.
- When the user picks Not now, then Flight Control stays quiet about that release and only speaks
  up again when a newer one comes out.
- When the user picks Update now, then Flight Control updates itself in one step and says in plain
  words what changed (the release title and a short list).
- When the update changed anything Claude only reads at session start (`CLAUDE.md`, skills, the
  `/afc` command, hooks, settings), then Claude says the new version takes effect after a restart and
  shows exactly how to exit and come back to this same conversation: type `/exit`, then reopen
  with `claude --continue` in the `A-FC` folder.
- When the user comes back that way, then the welcome confirms the new version is running
  (`You're on v0.02a now.`) and the conversation carries on where it was.
- When no newer release exists, the network is off, or the check fails, then the welcome says
  nothing about updates and the session starts as usual.
- When the update can't be applied safely (local edits in the `A-FC` folder, a different branch, a
  developer copy), then nothing is changed and Claude says why in one sentence and what to do.
- `sh bin/afc version` prints the installed version; `sh bin/afc update --check` and
  `sh bin/afc update` do the check and the update, each printing one JSON object.

## Out of scope

Publishing releases (still the user's own step); updating projects' code; updating add-ons.

## Design notes

- **What counts as newer.** Only published releases: `v*` tags on `main` on the GitHub remote.
  Work on `dev` or untagged commits on `main` never reach users. (Decided 2026-10-24.)
- **Knowing its own version.** A `VERSION` file at the root, bumped as part of each release;
  compared with the newest remote tag by version order, not by date.
- **The check.** Driven by the existing SessionStart hook (`afc/hooks/session_start.py`) via
  `git ls-remote --tags origin`, but the welcome never waits for the network: it answers from the
  saved result, and when the day's look is due it starts the look as a background process that
  saves its result for the next start. The look has one short time budget in all (every git call
  shares it); at most once a day (time stored in the workspace home, `~/.A-FC/`), result cached for
  the rest. A skipped release is stored there too, so "Not now" holds until a newer tag appears.
- **The update.** Fetch, then fast-forward the daily folder to the release tag (no merge, no
  history rewrite, no force). Before: refuse if `git status` isn't clean or the folder isn't on
  `main`. After: run `sh bin/afc check` and report.
- **Workspace upgrades.** `~/.A-FC/` records its layout number. Each release that changes the
  layout ships a numbered upgrade step in `afc/`; after the code update, Flight Control backs up
  `~/.A-FC/` to `~/.A-FC/backups/<date>-v<old>/` (projects' code folders are never touched), runs the
  missing steps in order, and restores the backup if one fails.
- **Developer copies.** A copy on `dev` or in maintenance mode never offers updates (FC-010).
- **Restart.** Claude Code can't reload its own instructions mid-session. The update compares the
  changed file list against the session-start files and only then asks for a restart. Coming
  back with `claude --continue` re-runs the SessionStart hook (its matcher already includes
  `resume`) and reloads `CLAUDE.md`; confirm against Claude Code's current docs that skills and
  settings reload on resume too. Leave a one-time "just updated to vX" note in `~/.A-FC/` for the
  welcome to show and then remove.

## Slices

- [x] 1. Flight Control knows its version — you'll check it by `sh bin/afc version` printing
      `v0.01a` (tests: `VERSION` file read, version ordering such as `v0.01a` < `v0.02a` < `v0.10a`)
- [x] 2. Check for a newer release — you'll check it by `sh bin/afc update --check` against a test
      remote with a newer tag, then with none, then offline (tests: `v*` tags only, short timeout,
      once a day, skipped release stays quiet, developer copy on `dev` or maintenance mode never
      offers)
- [x] 3. The welcome offers the update — you'll check it by starting a session on an older copy and
      seeing the one-line notice with 1. Update now 2. Not now; picking Not now and restarting shows
      nothing until a newer tag (tests in `tests/test_session_start.py` and
      `tests/test_session_start_update.py`)
- [x] 4. One-click update — you'll check it by picking Update now in an older test copy and landing
      on the newest tag with a plain "what changed" summary; a copy with local edits or on another
      branch is left untouched with a one-sentence reason (tests: fast-forward only, no force, clean
      `git status` required, `sh bin/afc check` runs after)
- [x] 5. Workspace data upgrades safely — you'll check it by updating a test copy whose `~/.A-FC/`
      is in the old layout and seeing projects still work, with a backup in `~/.A-FC/backups/`
      (tests: numbered upgrade steps run once each in order; a failed step restores the backup and
      says so)
- [x] 6. Restart and come back — you'll check it by an update that changes `CLAUDE.md`: Claude asks
      to `/exit` and reopen with `claude --continue`, and the welcome then says `You're on vX now.`
      once (tests: restart only when session-start files changed; one-time note shown then removed)
- [x] 7. README and CONTRIBUTING — you'll check it by the README describing the update offer instead
      of `git pull`, and CONTRIBUTING's release steps including the `VERSION` bump and any workspace
      upgrade step (content tests)

## Decisions

- 2026-10-24: Only published releases (`v*` tags on `main`) count as a newer version.
- 2026-10-24: "Not now" skips that release; the next offer comes with the next release.
- 2026-10-24: After an update that needs a restart, exit and resume the same conversation.
- 2026-10-24: When a release changes the workspace layout, the update backs up `~/.A-FC/` and
  upgrades it; a failed upgrade restores the backup.
- 2026-10-24: Slice 1 reports the last published release, `v0.02a`, not `v0.01a` as first written.
  This copy is built from v0.02a plus later work; reporting v0.01a would make the update check offer
  v0.02a to a copy that already has it. The welcome example above describes an older copy, so it is
  unchanged.
- 2026-10-25: Slice 1 approved as built. `sh bin/afc version` prints {"version": "v0.02a"}. Versions order by number, then letter, with a bare version before its letters, so 0.01a < 0.02a < 0.10a and 0.01a < 0.01b. Slices 2 to 7 are not built.
- 2026-10-25: The welcome never waits for the network (slice 3 review). A budget per git call let a
  silent origin hold it for 3 s, and a hung local git on top made it 6 s. The daily look now runs in
  the background and the offer shows from the next start; the branch is read from `.git/HEAD`, not
  by running git. Every git call of the look shares one budget.

## Shipped
