---
name: afc-drift
description: Use when a request, the next slice or the code seems to move away from the agreed intent or architecture, or the project's profile may have changed.
user-invocable: false
---

# Drift

Notice when the work moves away from what was agreed, and respond in proportion. Keep every message
short, ask one question per message, use plain words, and end with at most two numbered next steps,
the recommended one first.

## What to watch

Compare against `plan/intent.md` and `plan/architecture.md` in the workspace.

**Intent drift**
- A new request does not trace back to the goal or success in `intent.md`.
- Your own planned next slice does not serve the goal.
- A non-goal is quietly becoming a goal.
- The audience changes (only me → my team → customers).

**Code drift**
- Module boundaries or layers changed from `architecture.md`.
- A new dependency, service or external call appeared.
- A file is growing past 500 lines.
- Use `python3 -m afc graph impact <name>` to see what a change reaches before judging it.

**Profile drift**
- The purpose or audience changes, e.g. a personal prototype becomes a work tool, or real customer
  data arrives.

## Respond in proportion

- **Small drift** — one line, then carry on with their answer:
  "This is heading toward X instead of Y — still right?"
  1. Yes, X is right now (recommended if they have been asking for X) 2. Back to Y
- **The goal itself moved** — a short re-alignment interview using `afc-interview`'s rules: one
  question per message, only about what changed (goal, users, success, non-goals).
- **Code drift** — say what changed in one line and why it matters; either update `architecture.md`
  (the change is right) or plan a slice to bring the code back (it is not).

## Profile change

When the profile should change:

1. Re-ask only the profile questions that changed (see `afc-interview`).
2. Record it: `python3 -m afc set profile <profile>`.
3. Run `python3 -m afc modules` and compare with before. Tell the user "here's what's now missing"
   as a short list in plain words (e.g. sign-in for staff, logs that hide personal data, a private
   remote, a dependency check).
4. If it is now a work or enterprise project with a company wiki, hand off to `afc-enterprise`.
5. Turn the missing items into the next slices, smallest first.

## Record it

- Append to `plan/drift-notes.md`: date, what drifted, kind (intent / code / profile), what was
  decided.
- Update `plan/intent.md` (goal, non-goals, assumptions, open questions) when the intent changed.
- Record lasting decisions in `plan/decisions.md`.

Then go back to `afc-slice` with the next slice.
