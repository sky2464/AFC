# FC-028 — Welcome says it once

Size: S · Status: in progress · Started: 2026-10-25 · Done: -

Found on 2026-10-25 in an `A-FC-test` session. The welcome introduced Flight Control and offered
"Type 1 … 2 … or just say hi." The user said "hi", and the first reply introduced Flight Control
again ("Hi! I'm Flight Control, and I turn what you want to build into small working pieces.")
and asked the same 1/2 question in other words. Two intros and two copies of one question before
any work. (FC-023 stopped the welcome itself being shown twice; this is the reply after it.)

## Goal

After the welcome, the first reply never repeats it. A greeting gets a short hello and the
welcome's own question, without a second introduction.

## You'll know it works when

- `afc-start` says plainly: the welcome already introduced Flight Control, so the first reply has
  no self-introduction; on a greeting ("hi", "hello", "hey") it says hello in a few words and asks
  the welcome's question once, with the same 1/2 meanings.
- The health line, when there is one, stays one line after the question, not before it.
- A content test fails if `afc-start` loses that rule, and a live start with "hi" on the real
  `A-FC` folder (with maintenance mode off) shows one short line plus the question.

## Out of scope

The welcome banner's own text (`INTRO` in `afc/hooks/session_start.py`). The maintenance-mode
first reply, which already skips the start flow. Answers to 1 or 2, which already go straight in.

## Design notes

- One sentence in the First reply section of `.claude/skills/afc-start/SKILL.md`; the welcome's
  context line already carries what 1 and 2 mean, so nothing new is needed in the hook.
- Keep the skill short: replace "Otherwise answer briefly, then ask the question for the
  situation" rather than adding a paragraph.

## Slices

- [x] 1. No second introduction — you'll check it by `tests/test_content.py` (or
      `tests/test_fewer_questions.py`) checking that `afc-start` forbids a self-introduction in the
      first reply and asks the welcome's question once, and a live "hi" on a fresh start showing one
      short hello plus the question

## Decisions

## Shipped
