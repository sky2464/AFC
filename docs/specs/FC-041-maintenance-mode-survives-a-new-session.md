# FC-041 — Maintenance mode survives a new session

Size: M · Status: in progress

Found on 2026-10-26. The user was in maintenance mode, working on FC-040 (session `f79266d7…`).
Claude Code then started a new session in the same folder (`10701c43…`, a fork that kept the whole
conversation). Nobody turned maintenance mode off, but the switch is saved against the old
session's ID, so the new session read it as off. Its welcome offered "1 = continue php-vuln-checker" and the
user's "1", meant for the earlier question ("Build FC-040"), was taken as that. A slice was built in
the user's app, and had to be undone. FC-010 (the first maintenance mix-up) was meant to make this
impossible; FC-036 made the switch per session and removed the only thing that crossed a restart.

Two causes, both Flight Control's:

- **The switch belongs to a session ID, and a fork or /clear has a new one.** `afc/config.py` keeps
  `maintain.d/<session id>`. Nothing tells the new session that maintenance work was just under
  way here, and nothing stops project work until it knows.
- **A bare "1" is read against the welcome, not the conversation.** The welcome's context says "1 =
  continue <project>". When a restarted conversation already holds a question with its own
  numbered answers, `afc-start` doesn't say which one a bare number answers.

## Goal

A new session never guesses which world the user is in. When a fork or /clear follows recent
maintenance work, it asks one question first and shields every project until the user answers. A
bare number always answers the question just asked.

## Reaches the apps

Yes, in both directions. A user's project session can no longer be pulled into Flight Control work,
and a Flight Control session can no longer be taken for project work, so an app is never changed by
mistake (`afc/hooks/session_start.py`, `afc/hooks/rules_maintenance.py`, `afc/config.py`,
`.claude/skills/afc-start/SKILL.md`).

## You'll know it works when

- A new session that starts as `resume`, `fork` or `clear` with a session ID Flight Control hasn't seen
  before, in a copy where some other session turned maintenance mode on less than 12 hours ago,
  opens with one question and nothing else: "1. Keep working on Flight Control (recommended)
  2. Go to your project". A plain resume or compaction (same ID, seen in the last 30 days) a fresh `startup`, a flag older than 12 hours, or
  no flag at all never asks.
- Until the user answers, project work is blocked: project code writes and project git stop with a
  plain "Flight Control blocked: choose Flight Control or your project first" line. Answering 1 runs
  `sh bin/afc maintain on` (this session only); answering 2 runs `sh bin/afc maintain off`. Either
  one lifts the block.
- While a session is undecided, a shell (Bash) command runs only when it is on a short safe list:
  `sh bin/afc` with `maintain`, `status`, `plan` or `check`; plain read-only commands (`ls`, `cat`,
  `head`, `tail`, `grep`, `rg`, `find` without `-exec`/`-delete`, `pwd`, `echo`, `wc`, `sort`,
  `diff`); and read-only git (`git status`, `log`, `diff`, `show`, `branch` with no argument). Anything
  else, including any command with a redirect, pipe into a writer, `sed -i`, `python -c`, `touch`,
  `pushd`, `GIT_DIR=` or `env -C`, stops with the same "choose first" line. A list, not a hunt for
  every way to write: a form nobody listed is blocked.
- A bare 1 or 2 answers the question just asked in the conversation, not the welcome's. If it
  isn't clear which, `afc-start` asks one question. The one exception is an undecided session,
  where a bare 1 or 2 answers the undecided question and nothing else.
- In a live fork of a conversation that ends in a "1. Build … 2. Go back" menu, a bare "1" is
  taken as the mode answer (`maintain on`), the menu's action is not taken until the user answers
  it again, and a scratch project shows no change.
- A project session that is forked or cleared while no maintenance session is recent starts
  exactly as today (a fork that isn't asked about runs no welcome and none of its side effects).

## Out of scope

Making maintenance mode global again (FC-036). Changing what maintenance mode allows. The `source`
values Claude Code sends, which we only read. Carrying the mode over silently (the user chose to
be asked, 2026-10-26).

## Design notes

- "A session ID Flight Control hasn't seen" is an ID with no file `~/.A-FC/sessions.d/<id>` (touched
  by the hook at every start, pruned after 30 days) and no maintenance flag or `.ask` file of its own.
  A plain resume or compaction keeps its ID, so it finds one of them and never asks, including a
  session that began before the marks existed. A resume whose ID was never seen cannot be told from
  a fork, so only a genuinely unseen ID counts as new, and only with a flag under 12 hours old.
- "Undecided" is a file `maintain.d/<id>.ask`. `maintain on` and `maintain off` both remove it.
  The pretool guard reads it before anything else and blocks project code writes and project git
  while it exists; Flight Control's own folder is not blocked, so the session can still run
  `maintain on`/`off` and read the plan.
- An `.ask` file never lapses by time. It ends when `maintain on|off` answers it. The only cleanup is
  dropping an `.ask` older than 30 days (`SEEN_AFTER`, the same age as the seen marks), because after
  that the ID counts as unseen again and a flag older than 12 hours never asks. A session that
  starts again (any source) while its `.ask` is still there is asked once more. `maintain on|off`
  with no session ID is an error, not a success.
- In an undecided session a bare 1 or 2 is the answer to the undecided question and nothing else. If
  the conversation above ended in a numbered question of its own, it is not acted on: the reply says
  it still needs answering and repeats it. The context says "this session follows recent maintenance
  work", the same for a fork, a clear, or a re-ask on resume or compaction.
- A `fork` start that is not undecided prints no hook output and does none of the welcome's side
  effects, as before FC-041 (when `fork` matched no hook at all). The seen mark is still written, so
  a later resume of that fork is not taken for new.
- The question's text comes from the welcome's context; it is not left to the model. `afc-start`
  has a case for it ("Mode: undecided"): ask the question, nothing else, answer 1 with
  `sh bin/afc maintain on`, 2 with `sh bin/afc maintain off`.
- 12 hours is a number in `afc/config.py` (`ASK_WITHIN`), not a setting.
- Slice 1 measured the events (see Decisions). The 2026-10-26 incident was a fork: it had a new ID,
  kept the whole conversation, and the desktop app had forked the conversation several times.

## Slices

- [x] 1. See what a restart sends — you'll see it by a scratch copy whose hook writes each event's
      `source` and `session_id` to a scratch file for a real startup, `--continue` (resume), /clear
      and compaction, written in Decisions
- [x] 2. Ask when a fork or clear follows maintenance work — you'll see it by `sh bin/afc hook
      session_start` run with a scratch home: another session's flag 1 hour old plus `source: resume`
      and an unseen ID gives a context with "Mode: undecided" and the one question, and the same
      event again (ID now seen), `source: startup`, a flag 13 hours old, and no flag at all each
      give the normal welcome
- [x] 3. Nothing touches a project until answered — you'll see it by the pretool hook, in that
      scratch home with the `.ask` file present, blocking a Write into the project's code folder and
      a `git status` there with the "choose first" line, `maintain on` or `maintain off` removing
      the file, and the same Write then allowed after `maintain off`
- [x] 4. A bare number answers the last question — you'll see it by `afc-start` carrying the
      "undecided" case and the bare-number rule, and a live `claude --continue --fork-session -p 1`
      on a conversation that ends in a "Build / Go back" menu answering from the menu, with a
      scratch project showing no change
- [x] 5. Only a safe list of shell commands until answered — you'll see it by the pretool hook, in a
      scratch home with the `.ask` file present, allowing `sh bin/afc maintain status`, `ls`, `git status`
      and `cat` of a file, and blocking `sed -i`, `python3 -c "open(..,'w')"`, `touch`, `pushd .. && git
      status`, `GIT_DIR=.. git status`, `env -C .. git status`, `echo x > file` and `ls | tee file` with the "choose
      first" line, and `maintain off` then allowing the blocked ones again

## Tasks

Slice 2:
- `afc/config.py`: `ASK_WITHIN = 12 * 3600`; `seen(home, session)` touches `sessions.d/<id>` and
  returns whether it already existed or the ID has a flag or `.ask` (marks pruned at 30 days);
  `needs_choice(home, session, source, was_seen)` is true when `source` is `resume`, `fork` or `clear`, the ID was unseen, this session has no
  flag, and another session's flag is under `ASK_WITHIN` old. It writes `maintain.d/<id>.ask`.
- `afc/hooks/session_start.py`: `main` reads `source`, calls `seen` and `needs_choice` before
  `build_output`; when true the context says "Mode: undecided" with the question and that no
  project may be touched, and the welcome message carries the same one line.

Slice 3:
- `afc/hooks/rules_maintenance.py` (and `rules_paths.py` if the project paths live there): when
  `maintain.d/<id>.ask` exists, block project code writes and project git with the "choose first"
  line.
- `afc/config.py`: `set_maintain` (on or off) removes the `.ask` file.

Slice 5:
- `afc/hooks/rules_maintenance.py`: while `ctx.undecided`, `check_undecided` blocks every Bash command
  that is not wholly on the safe list (parse the raw tokens with `lex`; any redirect, pipe, `&&`/`;`
  chain, subshell, `-exec`, env-assignment prefix, or unparsable command counts as not on the list,
  except `a | b` or `a && b` where each part is itself on the list). Keep the existing project-reach
  check for Write/Edit tools. Never block `sh <path>/bin/afc maintain|status|plan|check`.

Slice 4:
- `.claude/skills/afc-start/SKILL.md`: a case for "Mode: undecided" and one sentence for the bare
  number rule, replacing lines rather than adding paragraphs.
- Run the live check and write the result in Decisions.

## Decisions

Slice 1, measured 2026-10-26 with Claude Code 2.1.310 in a scratch folder (a SessionStart hook that
only wrote `source` and `session_id`; run with `claude -p`, so no typed /clear; the folder is
discarded, nothing landed on `dev`):

- startup: `source: startup`, new ID (`5c170ff2`).
- `--continue` (resume): `source: resume`, the SAME ID (`5c170ff2`). `--resume <id>` the same.
- compaction (`/compact`): `source: compact`, the SAME ID.
- `/clear`: `source: clear`, a NEW ID (`56dc4aa8`).
- `--continue --fork-session`: `source: resume`, a NEW ID (`c70a583f`). Later (slice 4, fix 1):
  "resume" was seen in one headless run and "fork" in another; both are handled.

So `source` is always sent, but the ID changes only on /clear and on a fork, not on a plain resume or
compaction. Slice 2 as written (carry on resume, clear, compact) is still safe, but a plain resume
or compact needs no carrying because `maintain.d/<id>` is already there; the carry matters for
`clear` and for a forked resume. This does not explain the 2026-10-26 incident (new ID `10701c43`,
source unknown): the spec is adjusted before slice 2 is built, and the first adjustment to check
is what source the incident's session sent. Stopped here as the slice says.

- 2026-10-26: the incident was a fork (new ID, conversation kept, `source: resume`). A fork or /clear
  cannot tell by itself whether it continues maintenance work, so the user chose to be asked first
  over carrying the mode silently: one question at the start, and project work blocked until it is
  answered. Slices 2 to 4 rewritten to match.

Slice 3, tried 2026-10-26 with the pretool hook in a scratch home (one registered scratch project
with a git folder, `maintain.d/other` as the recent flag, `maintain.d/sess1.ask` present):

- With `sess1.ask`: a Write into the project's code folder, `git status` in it, and
  `git -C <project> status` run from the A-FC folder were each stopped with exit 2 and "Flight
  Control blocked: choose Flight Control or your project first". Reading a file in the project's
  workspace (the plan) and `sh bin/afc maintain status|on|off` run from the A-FC folder were
  allowed (exit 0). A session without an `.ask` file (`sess2`) writing to the project was allowed.
- `AFC_SESSION=sess1 sh bin/afc maintain off` removed `sess1.ask` (and made no flag); the same
  Write and `git status` were then allowed. `maintain on` also removed the file and left
  `maintain.d/sess1`; the Write was then stopped by the normal maintenance-mode line instead.
- The guard is a separate rule, `check_undecided`, placed before `check_paths` in the pretool list,
  so the "choose first" line wins over other blocks. It reuses the project-reach test of
  `check_maintenance` (now `_reach`), so the two cannot drift. `Context` has an `undecided` field.
- Not mine, seen on the way: `sh bin/afc ...` typed with a project folder as the working directory is
  "couldn't read this command safely" (by `check_paths`, with or without an `.ask` file). The
  session runs the maintain commands from the A-FC folder, as `afc-start` does, so this does not
  get in the way.

Slice 4, tried 2026-10-26 with Claude Code 2.1.310. `afc-start` now has the "Mode: undecided" case
(ask the one question; 1 runs `maintain on`, 2 runs `maintain off`; no project touched until
answered) and one sentence on the bare number (a question with numbered answers already in the
conversation is what a bare 1 or 2 answers; if unclear, ask one question). 40 lines to 44, limit 500.
Live check in `/private/tmp/claude-501/.../scratchpad/fc041live` (a scratch copy of this repo on
`dev`, a scratch `AFC_HOME` with one scratch project and a fresh flag `maintain.d/oldsession`;
`AFC_SESSION` and `CLAUDE_CODE_SESSION_ID` unset for the child, so it could not inherit this
session's ID). Step 1: `claude -p` with a prompt to reply only "1. Build FC-040 / 2. Go back to your
projects". Step 2: `claude --continue --fork-session -p 1`.

- As shipped, the fork gets no hook at all. 2.1.310 sends `source: "fork"` for
  `--continue --fork-session -p` (measured with an empty matcher and a hook that logged its input;
  new ID `7f44d4e7`), not `resume` as slice 1 recorded. The settings.json matcher
  `startup|resume|clear|compact` does not match it, so no SessionStart ran, no sessions.d or
  `.ask` file was written, and there was no "Mode: undecided". The reply answered from the menu
  ("FC-040 is work on Flight Control itself, maintenance mode is off ... turn it on, then build"), did
  not build, and the scratch project showed `git status --short` empty and only the `init` commit.
  This run happened three times with the same result.
- With a scratch-only patch (matcher `""`, and `fork` added to the sources in `needs_choice`) the hook
  asked: `SessionStart:fork` gave "Mode: undecided" and a `.ask` file; the model, following the
  context line ("if the first message is 1, run sh bin/afc maintain on"), ran `maintain on` (flag
  written, `.ask` gone) and replied "Maintenance mode is on ... 1. Build FC-040 (recommended) 2. Look at
  the plan first". It built nothing. The scratch project: `git status --short` empty, one commit.
  Here the 1 was taken as the undecided question's 1, which coincides with the menu's "Build"; the
  run cannot tell the two apart, and no run was made where they differ.
- So the slice 4 skill text is in place, but two things are not met and are left for the next
  slice or spec change: (a) the `fork` source must be handled (matcher and `needs_choice`), or a
  real fork never asks; (b) the undecided context line tells the model to treat a first-message 1
  as the welcome's answer, which contradicts the bare-number rule when the conversation already
  ends in a menu. Neither was changed here. The line "answering from the menu" was seen only with
  no hook (unpatched), not with the ask in place.

Fix 2, 2026-10-26 (a second checker found three breaks; the user decided each):

- A. An unanswered question no longer lapses: `ASK_EXPIRES` and the 24-hour lift are gone from
  `undecided()`; an `.ask` stays until `maintain on|off`. The only cleanup is `_prune_asks`, run by
  `seen()`, which drops an `.ask` older than 30 days. Scratch home: an `.ask` 25 days old still gave
  "Mode: undecided" on a `compact` start; one 40 days old was removed by the next `seen()`.
- B. In an undecided session a bare 1 or 2 answers the undecided question only. The context line
  (`_undecided_output`) and the Undecided case of `afc-start` (and its bare-number sentence) now say
  so, and say that a numbered question of the conversation's own is not acted on but repeated.
- C. A `fork` start that is not undecided prints nothing and does none of the welcome's side effects
  (no update note or look, no add-on or connector settings writes, no `_save_session`). Scratch home,
  real hook: a fork with no flag gave exit 0 and 0 bytes of output, and wrote no line to the env file
  (a `startup` wrote `export AFC_SESSION=s2`); only the seen mark was written. With a recent flag the
  same fork asked; the same ID again as `resume` asked again. A-FC's tracked `.claude/settings.json`
  showed no `git diff` afterwards.
- D. The undecided context is neutral: "this session follows recent maintenance work".
- E. Live check again, real hook, no scratch patch (Claude Code 2.1.310; scratch copy of the repo on
  `dev` with this change applied, in `.../scratchpad/fc041live2`; scratch `AFC_HOME` with one scratch
  project, a git repo with one commit; a fresh flag `maintain.d/oldsession`; `AFC_SESSION` and
  `CLAUDE_CODE_SESSION_ID` unset for the child). Step 1 `claude -p` replied "1. Build FC-040  2. Go
  back to your projects". Step 2 `claude --continue --fork-session -p 1`:
  - Asked: yes. The event was `SessionStart:fork` and its output was the "Mode: undecided" welcome.
  - The reply ran `sh bin/afc maintain on` (the only tool call), and said: "Maintenance mode is on,
    so we're working on Flight Control itself. Your "1" answered that question, so I haven't started
    anything yet. The earlier question still needs an answer: 1. Build FC-040  2. Go back to your
    projects".
  - `maintain on` ran: yes. The new session now has its own flag and no `.ask`.
  - The menu's action ("Build FC-040") was not taken. The scratch project's `git status --short` was
    empty and its log is the single `init` commit.
  - This is one run; the model's wording will vary.

Slice 5, tried 2026-10-26 with the real pretool hook (`sh bin/afc hook pretool`, JSON events piped in)
in a scratch home `.../scratchpad/s5` (one scratch project with its own git folder, `maintain.d/other`
as the recent flag, `maintain.d/sess1.ask` for the session, events sent from the A-FC folder):

- Allowed (exit 0, no output): `sh bin/afc maintain status`, `sh <full path>/bin/afc plan`, `sh bin/afc
  check`, `python3 -m afc maintain status`, `ls`, `ls -la /private/tmp`, `cat`, `head`, `grep -r`, `rg`,
  `find . -name '*.py'`, `pwd`, `echo`, `wc`, `sort`, `diff`, `git status|log --oneline|diff|show
  HEAD|branch`, `ls | head -3`, `git status && ls`, a three-part pipe. With the project as the working
  folder `ls` and `cat a.txt` were allowed and `git status` / `git log` were stopped (project git, as
  in slice 3); the same `git status` from session `sess2` (no `.ask`) was allowed.
- Stopped with exit 2 and "Flight Control blocked: choose Flight Control or your project first": the
  listed ones (`sed -i`, `python3 -c "open(..,'w')"`, `touch`, `pushd .. && git status`, `GIT_DIR=.. git
  status`, `env -C .. git status`, `echo x > file`, `ls | tee file`) and also `ls; touch x`, `git status
  $(touch x)`, a backtick substitution, `cat <(touch x)`, `FOO=1 git status`, `git -c core.pager='touch x'
  log`, `git -C <project> status`, `git diff --output=file`, `--outp=file` (git accepts shortened
  options), `git log --output=f`, `find -exec|-delete|-fprint`, `sort -o|-ro|--output`, `rg --pre`,
  `bash -c`, `sh -c`, `sh bin/afc maintain status; touch x`, `sh bin/afc set|new` (not one of the four
  words), `node -e`, `./ls`, `/bin/ls`, `ls || touch x`, `ls & touch x`, `(ls)`, `cat <<EOF`, `ls >> f`,
  `ls 2>&1`, `git branch newb`, `git branch -D x`, `git checkout`, `git commit`, `env ls`, `tee f`,
  `ls && touch x` (the writer on the right of an `&&`). 71 commands in all: 64 allowed after the
  answer, 7 stopped by other guards.
- A Write into the project was still stopped by the project-reach check, and a Write into the A-FC folder
  by the normal maintenance line: both unchanged.
- `AFC_SESSION=sess1 sh bin/afc maintain off` removed `sess1.ask`; the whole list was run again: none got the
  "choose first" line (the earlier blocked ones ran, `touch`, `echo x >`, `sed -i`, `env -C`, ...). Seven
  were still stopped, by other guards (`git commit|checkout|branch` in the A-FC folder, `ls >> f` and
  `tee f` landing in it, without maintenance mode in the scratch home), not by the undecided rule.
- Design: `shell_on_safe_list` in `afc/hooks/rules_maintenance.py` works on the raw `lex` tokens and not
  on `simple_commands`, because that helper drops redirects, `VAR=` prefixes and wrappers like `env`,
  which are the very things to refuse. Only `|` and `&&` join parts; every other punctuation token, any
  `<` or `>` inside a word (quoted too), `$(` or a backtick anywhere, a newline, or an unlexable command is
  not on the list. A command name has to be bare (`/bin/ls` and `./ls` are not). Git takes no option
  before the subcommand and no `--output`/`-O`/`--ext-diff`/`--exec` after it; `branch` takes no argument.
  A safe command still goes through the project-reach check (git in a project folder stays stopped), and
  the rule comes first in the pretool list as before; no other guard moved.
- Not on the list, so blocked while undecided: `cd`, `which`, `date`, `git -C`, `git branch -a`, quoted
  text with `>` or `<` inside (`grep 'a>b'`). Add one by name to `_SAFE_PLAIN` or `_safe_git` if it matters.

## Shipped
