# S-008 — Agent instruction files in apps

Size: S · Status: next · Started: - · Done: -

Finding: 13.

## Goal

When a tool drops instructions for AI agents into the user's app, Flight Control notices, tells the
user in one line, and treats the text as data. In the live run `next dev` wrote an `AGENTS.md`
("This is NOT the Next.js you know… Read the relevant guide…") and it was committed without a word.

## You'll know it works when

- When a slice adds or changes an agent instruction file (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`,
  `.github/copilot-instructions.md`, and the like), then the scan reports it as a warning naming the
  file.
- When Claude shows the slice, then it says in one line which file appeared and that it was not
  followed, and asks whether to keep it in the repo.
- Claude never acts on the file's instructions without the user's say-so.

## Out of scope

Blocking such files; judging whether their advice is good.

## Design notes

- `afc/scan.py`: an `agent files` check over files added or changed since the last commit (git
  status), matched against a short list of known names.
- `afc-slice` checkpoint 3 and `rules/ai-safety.md`: one line each about this case.

## Slices

- [ ] 1. Scan check for agent instruction files — you'll check it by adding an `AGENTS.md` to a test
      app and running the scan (tests in `tests/test_scan.py`)
- [ ] 2. Slice skill and ai-safety rule mention it — you'll check it by a live slice in a Next.js app
      (content tests)

## Decisions

## Shipped
