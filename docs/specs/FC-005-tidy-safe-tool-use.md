# FC-005 — Tidy, safe tool use

Size: M · Status: next · Started: - · Done: -

Findings: 9, 16, 17, 18, 21.

## Goal

Claude works quietly and safely: no walls of text on screen, files written through the tools the
guards fully check, no lost working folder, and nothing outside the project touched. In the live run
it printed five rule files with `cat`, guessed where rules live, wrote every file through shell
heredocs, kept changing folders, logged to `/tmp/x` and stopped servers with `pkill -f "next dev"`.

## You'll know it works when

- When Claude needs a rule module or spec, then it reads it with the file-reading tool at the exact
  path from `sh bin/afc modules`, and nothing is printed to the user.
- When Claude creates or changes a file, then it uses the file tools, not `cat > … <<`.
- When Claude runs Flight Control, then it uses the absolute launcher path from the context line and
  never `cd`s to get back.
- When a slice starts a dev server, then it uses a free port, records the process ID, writes the log
  into the project workspace's `reports/` folder, and stops only that process.
- When a command would stop processes by pattern (`pkill -f`, `killall`), then the guard blocks it
  with a plain reason.

## Out of scope

Blocking all shell file writes (too broad); process sandboxing.

## Design notes

- `sh bin/afc modules` returns absolute `path` values for each module, not just names.
- The welcome context adds `Flight Control: <absolute path to bin/afc>`.
- New guard rule in `afc/hooks/` (its own small module, e.g. `rules_process.py`) for `pkill -f`,
  `pkill` with a pattern, and `killall`; plain `kill <pid>` stays allowed. Tests beside the other
  guard tests.
- `afc-slice` gains a short "How to work" block: file tools for files, Read for rules and specs, no
  `cd`, how to run and stop a dev server.

## Slices

- [ ] 1. `modules` returns paths and the context line names the launcher — you'll check it by running
      both (tests in `tests/test_cli.py`, `tests/test_session_start.py`)
- [ ] 2. Guard blocks pattern kills — you'll check it by asking Claude to run `pkill -f node` and
      seeing a plain block (tests in a new `tests/test_guard_process.py`)
- [ ] 3. Slice skill "How to work" rules — you'll check it by a live slice with no `cat` of rules, no
      heredoc writes and no `cd` back (content tests on `afc-slice`)

## Decisions

## Shipped
