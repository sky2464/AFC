# FC-050 — Right model for each job

Size: M · Status: in progress · Started: 2026-10-26 · Done: -
Area: tokens

Asked for on 2026-10-26: architecture changes only by the newest Opus at high effort ("the most
critical piece"), unless the user overrules it; spec planning and interviews by Opus; builds by
Sonnet; documents and lighter tasks by Haiku.

FC-021 and FC-022 already route four roles (`afc/role_agents.py`): research Haiku, plan Opus, build
Sonnet, check Haiku. What is missing, checked on `dev` on 2026-10-26:

- **No architecture role.** `plan/architecture.md`, structure decisions and (soon, FC-049)
  `docs/architecture.md` are written by whichever model the main session happens to be on. If the
  user picked Sonnet, the most critical notes are Sonnet's.
- **Interviews and spec questions run in the main session** (`afc-interview`, `afc-start`), so they
  use whatever `/model` says. Nothing in Flight Control sets that model, and the routing file's own
  note only says "not Haiku".
- **No documents role.** Changelog wording, README lines, plan bookkeeping text and findings intake
  are written by the main session or the Sonnet builder.
- **No effort setting at all.** Models are routed; thinking effort is not, so "high thinking" cannot
  be asked for.
- **Nothing says when the routing is defeated.** Claude Code's own order puts a model or effort that
  Claude passes when it invokes an agent above the agent file, and the environment variables
  `CLAUDE_CODE_EFFORT_LEVEL` and `CLAUDE_CODE_SUBAGENT_MODEL` above or below it depending on the
  setting. Any of them can make an architect run on Sonnet with no warning.

What the Claude Code docs say (checked 2026-10-26): agent files take `model` (aliases `opus`,
`sonnet`, `haiku` or a full ID) and `effort` (`low` to `max`; the levels depend on the model); aliases
point to the newest version on the Anthropic API, and to older ones on some other providers; a
skill's own `model` and `effort` last only for the current turn, so they cannot hold a multi-turn
interview on one model; a project settings file's `model` sets the main session's model and `/model`
still overrules it.

## Goal

Every kind of work runs on the model and effort it deserves, by default and with no step for the
user: architecture on the newest Opus at high effort, spec planning and interviews on Opus, builds on
Sonnet, documents and light work on Haiku. The user can overrule any of it in one place, and
Flight Control says plainly when something else is overriding it.

## Reaches the apps

Yes, this is for the apps. Every project gets the new `afc-architect` and `afc-docs` agents beside the
four it has, `agents/routing.json` in its workspace gains effort and the new roles, and the
architecture, interview and slice skills hand their work to those agents
(`templates/project/agents/`, `templates/workspace/agents/routing.json`, `afc/project_agents.py`,
`afc/role_agents.py`, `.claude/skills/afc-architecture`, `.claude/skills/afc-slice`).

## You'll know it works when

- A1. There are six roles: research (Haiku), plan (Opus), architect (Opus, effort high), build
  (Sonnet), check (Haiku), docs (Haiku, effort low). `sh bin/afc agents` prints the model and effort
  for each, in plain words, and says that `opus`, `sonnet` and `haiku` mean the newest version on the
  Anthropic API and how to pin a full ID.
- A2. In a new project, `.claude/agents/` has `afc-architect` (with `model: opus` and `effort: high`)
  and `afc-docs` (`model: haiku`, `effort: low`) written from the workspace routing file; changing
  one role in `agents/routing.json` and running `sh bin/afc agents sync` rewrites that agent file
  and no other.
- A3. After a slice that changes structure (a new module, boundary, dependency or outside call), the
  architecture notes and any structure decision are written by `afc-architect`, never by the main
  session or the builder. The `afc-slice` and `afc-architecture` skills say so in one sentence each.
- A4. Before a structural slice is built, `afc-architect` adds a short design note to the spec's
  Design notes. Flight Control's own build workflow does the same when `check` reports a new module
  that no row of `docs/architecture.md` names (FC-049's `architecture_unmapped`).
- A5. Changelog and release wording, README edits, findings intake text and plan bookkeeping text go
  to `afc-docs`; the skills and the builder instructions say so, and none of these is done by the
  builder.
- A6. A Flight Control session starts on Opus: the tracked `.claude/settings.json` sets `model` to
  `opus`. `/model` in the session, or a `model` line in `.claude/settings.local.json`, overrules it,
  and Flight Control never writes it back. `sh bin/afc agents` prints the main model setting and
  where to change it.
- A7. `sh bin/afc check` reports `routing_overridden` when `CLAUDE_CODE_SUBAGENT_MODEL`,
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` or `CLAUDE_CODE_EFFORT_LEVEL` is set (it would replace the
  routing), and `routing_drift` (fixable by `agents sync`) when an agent file's model or effort
  differs from the routing file.
- A8. Every agent and skill instruction that calls an agent says never to pass `model` or `effort`
  for it, because a value passed at call time outranks the agent file.
- A9. Measured live on a scratch project: an architecture request runs `afc-architect` on the Opus
  model name at effort high, a slice build runs `afc-build` on Sonnet, a changelog request runs
  `afc-docs` on Haiku, and the three model names and efforts are written in Decisions.

## Out of scope

Choosing models for Jev (FC-024). Token cost reporting (FC-025). Forcing a model on the user's own
`/model` choice. Changing the model of the main conversation from a skill or hook (the docs say
neither can set it persistently). Provider-specific model IDs beyond the existing note for Bedrock
and Vertex.

## Design notes

- Only agent files and the routing file enforce a model, because a skill's `model:` lasts one turn and
  cannot honour the user's overrule. So architecture work is done by an agent, and the user overrules
  it by editing `agents/routing.json` (or `sh bin/afc agents set architect sonnet`), which also
  rewrites the agent file.
- Routing file shape: `roles.<role>` may be a model string (as today) or `{"model": "...", "effort":
  "..."}`. A missing role uses the defaults, so existing files keep working.
- Defaults live in `afc/role_agents.py` (`DEFAULT_MODELS`, a new `DEFAULT_EFFORT`, `ROLES` gets
  `architect` and `docs`; `PROJECT_AGENT` and `MAINTENANCE_AGENT` get their names).
  `set_agent_model` is joined by `set_agent_effort`; both only touch frontmatter.
- Interviews and spec questions need the user's answers, so they stay in the main session and take
  its model (Opus by A6). The research behind them (web lookups, reading code) already goes to
  `afc-research` on Haiku, and the drafting of intent and specs to `afc-plan` on Opus.
- Why a default `model` in the tracked settings file: Claude Code reads it before any hook runs, so
  the first start is already on Opus (the same reason FC-038 uses a tracked file). `/model` always
  outranks it, so "unless the user overrules it" holds without Flight Control tracking anything.
- The plan role keeps the session's effort. Only the architect is pinned to high, as asked.
- `routing_overridden` reads the environment of the process running `check`. That is the same
  environment Claude Code's own session uses, so it sees what would apply.
- What is not documented and slice 1 settles: whether `effort: high` is accepted on every model the
  alias can resolve to. If a model rejects it, the agent file falls back to no `effort` line and
  `agents` says so.
- Provider note: on Bedrock and Vertex an alias may point to an older version (the docs say so), so
  `agents` repeats the pin-a-full-ID line there.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Six roles with effort — you'll see it by `sh bin/afc agents` on a scratch project printing
      six roles with model and effort, `agents set architect sonnet` changing only that agent file,
      and the effort line accepted by a live `claude -p` call on each model (proves A1, A2)
- [x] 2. Architecture goes to the architect — you'll see it by the skill sentences, and a scratch
      slice that changes structure ending with its `architecture.md` row written by `afc-architect`
      (proves A3, A4)
- [x] 3. Documents go to Haiku — you'll see it by a scratch changelog request answered by `afc-docs`
      and the builder instructions refusing to write it (proves A5)
- [x] 4. Opus by default, one place to overrule — you'll see it by `.claude/settings.json` setting
      the model, `agents` printing where to change it, and a `model` line in
      `.claude/settings.local.json` winning in a scratch start (proves A6)
- [ ] 5. Nothing silently defeats it — you'll see it by `check` reporting `routing_overridden` with
      the variable set and `routing_drift` with one edited agent file, `agents sync` clearing the
      second, and every calling instruction carrying the no-`model`-argument line (proves A7, A8)
- [ ] 6. Measured live — you'll see it by a scratch project run for the three requests with the
      model name and effort of each agent read from the session transcript and written in Decisions
      (proves A9)

## Tasks

Slice 1:
- `afc/role_agents.py`: `ROLES` adds `architect`, `docs`; `DEFAULT_EFFORT`; `resolve_effort`;
  `set_agent_effort`; `routing_summary` returns effort and the alias note.
- `templates/project/agents/afc-architect.md`, `afc-docs.md` (new); `.claude/agents/afc-architect.md`,
  `afc-docs.md` (new, for Flight Control's own builds).
- `afc/cli_agents.py`: print effort; `agents set <role> <model> [--effort <level>]`; `agents sync`.
- `afc/project_agents.py`: install the two new agents and write effort.

Slice 2:
- `.claude/skills/afc-architecture/SKILL.md`, `.claude/skills/afc-slice/SKILL.md`: one sentence each:
  hand architecture and structure decisions to `afc-architect`.
- `.claude/workflows/afc-build-spec.js`, `templates/project/workflows/afc-build-slice.js`: an
  architect step before a structural slice, and after it when `check` reports an unmapped module.
- `afc/cli_slice.py`: `slice record --architecture` text comes from the architect's note.

Slice 3:
- `.claude/skills/afc-slice/SKILL.md`, `.claude/skills/afc-deliver/SKILL.md`,
  `.claude/agents/afc-builder.md`, `templates/project/agents/afc-build.md`: changelog, README, findings
  intake and plan text go to `afc-docs`.

Slice 4:
- `.claude/settings.json`: `"model": "opus"`.
- `afc/cli_agents.py`: print the main model setting and where to change it.
- `templates/workspace/agents/routing.json`: notes updated (main session defaults to Opus; pin a full
  ID on other providers).

Slice 5:
- `afc/cli_health.py`: `routing_overridden`, `routing_drift` (fixable).
- Every skill or agent file that calls an agent: add the line "Never pass `model` or `effort` when you
  call an agent; the agent file decides."

Slice 6:
- Run the three requests in a scratch project, read the model and effort from the transcript, and
  write them in Decisions. Never use a real project.

## Decisions

- 2026-10-26 (slice 1): scratch `install_code_agents` writes six agents; `agents set architect sonnet` rewrites only
  `afc-architect.md`. Live `claude -p` accepts `--effort low` on haiku, default on sonnet, and `--effort high` on opus.
- 2026-10-26 (slice 2): both build workflows take `structural: [slice numbers]`; `afc-architect` writes the design
  note before those slices and the architecture update after them (FC's workflow also after any slice that leaves
  `architecture_unmapped`). Scratch run: a session told about a new outside-call module called `afc-architect`
  with no model argument; it ran on claude-opus-5-5 at effort high and wrote the `src/payments.py` row itself.
- 2026-10-26 (slice 3): `afc-slice`, `afc-deliver`, `afc-builder` and the project `afc-build` route changelog, README,
  findings and plan text to `afc-docs`; ticking the slice box stays with the builder. Scratch run: a changelog
  request went to `afc-docs` on claude-haiku-5-5 at effort low and wrote the line; `afc-build` given the same task
  refused it and named `afc-docs`.
- 2026-10-26 (slice 4): tracked `.claude/settings.json` sets `"model": "opus"`; `agents` prints `main_session`
  (model, the file or `ANTHROPIC_MODEL` that sets it, and how to change it). Scratch start: `settings.json` opus
  alone ran claude-opus-5-5; adding `{"model": "haiku"}` in `settings.local.json` ran claude-haiku-5-5.

## Shipped
