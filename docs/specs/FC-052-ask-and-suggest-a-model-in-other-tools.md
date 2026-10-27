# FC-052 — Ask and suggest a model in other tools

Size: M · Status: in progress · Started: 2026-10-27 · Done: -
Area: tokens

Asked for on 2026-10-27. FC-050 gives every job its model (architect Opus high, plan Opus, build
Sonnet, research and check Haiku, docs Haiku low), but only through Claude Code agent files and the
workspace `agents/routing.json`. FC-051 made Flight Control work in Cursor, Codex, Copilot and
Antigravity through `AGENTS.md`, but its Out of scope left subagent routing as Claude-only. So in
Cursor today the whole session, architecture notes included, runs on whatever model the user picked
in the chat, and nothing says so.

What the tools' local settings show, seen on this machine on 2026-10-27 (slice 1 confirms):

| Tool | Where the model shows | What it holds |
|---|---|---|
| Cursor (CLI and agent) | `~/.cursor/cli-config.json` | `model.modelId` and `model.displayName` (for example `composer-2.5`), `selectedModel`, `exploreSubagentModel` |
| Cursor (IDE chat) | the app's own state database | not readable as a plain file; treated as "not shown" |
| Codex | `~/.codex/config.toml` | `model` and `model_reasoning_effort` |
| Copilot | no plain settings file known | treated as "not shown" |
| Antigravity | `~/.gemini/` folder | no plain model key found on this machine; treated as "not shown" |

A Cursor shell also carries `CURSOR_AGENT=1`, which says which tool is running.

## Goal

When Flight Control runs in a tool other than Claude Code, it asks in plain words which model to use
for this project, once. If the user already has a model in that tool's settings, it can suggest
keeping it or switching to a better fit those settings show. If the user does not know which model
to pick (or no model is shown), it checks the local environment and a short public look-up for what
is current, then offers three numbered choices: top tier (premium), best for cost, and hybrid (best
balance of quality and cost). "Cost" here means what that tool usually includes on a subscription
plan (Cursor, Copilot, Codex, Antigravity and the like), not pay-per-token API keys. For heavy jobs
(architecture and spec planning) it asks again if the chosen model is a light one. It never changes
the tool's settings itself; the user switches in the tool's own model picker.

## Reaches the apps

Yes. Every project worked on from Cursor, Codex, Copilot or Antigravity gets the ask: the start flow
(`AGENTS.md` preface, `.claude/skills/afc-start`) and `afc-slice` ask it, and the answer is kept per
tool in the project's workspace `agents/routing.json` (`templates/workspace/agents/routing.json`).
Nothing is written into the app's code folder.

## You'll know it works when

- A1. `sh bin/afc model` says which tool is running (Claude Code, Cursor, Codex, Copilot,
  Antigravity or unknown), the model that tool's local settings show and the file it came from, or
  "not shown" when no readable file holds it.
- A2. When a current model is shown, `sh bin/afc model --role <role>` may name one switch suggestion
  drawn from models that tool's settings show, with a one-line reason, only when the job's need
  (strong for architect and plan, balanced for build, light for research, check and docs) differs
  from the current model. With no fit among shown models, there is no single-switch suggestion.
- A3. When the user does not know, or no model is shown, `sh bin/afc model --options` (or the start
  ask) combines the local check with a short public look-up of current models for that tool, and
  returns exactly three options with one-line reasons: (1) top tier / premium (highest quality on
  that tool's subscription), (2) best for cost (lighter model that still works for everyday work on
  the same plan), (3) hybrid for quality and cost. The recommended one is named. Reasons talk about
  plan / subscription use, not API keys or token prices. Model names and versions always come from
  that look-up or from the tool's own settings — never from a list shipped inside Flight Control.
  If the look-up fails, it uses a cache of the last successful look-up on this machine (with its
  date) when one exists; otherwise it offers only what local settings already list and says it
  could not refresh.
- A4. In a non-Claude tool, the first reply of a project session asks one question. With a shown
  model: at most two answers (keep it, or switch to the single suggestion). With no shown model or
  "I don't know": exactly three numbered answers (premium, best cost, hybrid), recommended first.
- A5. The answer is kept per tool in the workspace `agents/routing.json` (`sh bin/afc model choose
  <model>`). The next session in the same tool does not ask again unless the tool's settings now show
  a different model. Flight Control never writes Cursor's, Codex's or any other tool's settings.
- A6. Before architecture work or spec planning in a non-Claude tool, when the kept model is a light
  one, Flight Control asks once in that session whether to switch to the strong fit (from settings
  if shown, else from the three-option set). Builds and lighter jobs do not ask.
- A7. In Claude Code nothing changes: `model` says Claude Code and points to `sh bin/afc agents`,
  no ask appears, and FC-050's routing and its `routing_overridden` warning work as before.
- A8. `sh bin/afc check` adds, to each tool's line, the model its settings show (or "not shown")
  and the one kept for the active project.
- A9. Measured live in Cursor on a scratch project: a "don't know" start shows three options from
  local plus look-up (or fallback), the choice is kept, a second session does not ask, and an
  architecture request on a light model asks once; the model names are written in Decisions.

## Out of scope

- Claude Code's own warning when something overrides the model set for each job
  (`routing_overridden`, `routing_drift`). That stays in FC-050.
- Switching the model for the user, or writing any tool's settings or state database.
- Per-job subagent routing in other tools (each job on its own model inside one chat). Cursor and
  the others pick one chat model; this spec asks and suggests, it does not route.
- Reading the IDE chat pick from app databases (only plain local settings files plus the agreed
  public look-up).
- Buying, billing, opening accounts, or quoting subscription prices; "best for cost" is a plain
  ranking of models on the tool's plan, not a price or an API-key bill.
- Requiring or collecting an API key; these tools are treated as subscription / in-app model pickers.
- Shipping model names or version IDs inside the Flight Control repo (they go stale). Current names
  come only from the tool's settings, a live look-up, or a per-machine cache of a past look-up.

## Assumptions to confirm

- [x] Cursor's `~/.cursor/cli-config.json` `model.modelId` is the model the Cursor agent is using
  in the CLI; the IDE chat's pick is not in a plain file, so it is "not shown" there.
  (Checked 2026-10-27: `CURSOR_AGENT=1` and `modelId` `composer-2.5`.)
- [x] `CURSOR_AGENT=1` is set in every shell the Cursor agent runs; Codex, Copilot and Antigravity
  each set a variable of their own that names them (or Flight Control falls back to "unknown").
  (Checked 2026-10-27: Cursor sets `CURSOR_AGENT`; detection also accepts `CODEX_HOME` /
  `CODEX_SANDBOX`, `COPILOT_CLI` / `GITHUB_COPILOT`, `GEMINI_CLI` / `ANTIGRAVITY`.)
- [x] Codex `~/.codex/config.toml` `model` is the model Codex runs with unless `-m` overrides it.
  (Checked 2026-10-27: this machine has `model = "gpt-6.1-sol"`.)
- [x] Antigravity keeps a readable model setting under `~/.gemini/`; if not, it is "not shown".
  (Checked 2026-10-27: settings and config have no model key → "not shown".)
- [x] Family name rules (not version IDs) sort models into strong, balanced and light well enough
  (for example names containing `opus`, `pro` or `max` as strong; `sonnet` as balanced; `haiku`,
  `flash`, `mini`, `nano` or `composer` as light). Rules never pin a year or a full model ID.
  (Checked 2026-10-27: token-bounded family words; `mini` does not match inside `gemini`.)
- [x] A short public look-up (vendor docs or product pages about models on that tool's plan) can
  name current models without an API key or login. When it cannot, a per-machine cache of the last
  successful look-up (under `~/.A-FC/`, not in the repo) or the tool's own local settings is enough
  to keep asking without inventing names.
  (Checked 2026-10-27: Cursor docs look-up returned live names; `AFC_MODEL_LOOKUP=off` used the
  machine cache and said so; empty local + no cache invents nothing.)

## Design notes

- Slice 1 layout: `afc/tool_model.py` is read-only (environment plus home-folder settings files,
  no network, no workspace writes) and lives with the measurement modules beside
  `tool_coverage.py`; `afc/cli_model.py` is a thin CLI wrapper that only prints. Writes
  (`model choose`) and the public look-up arrive in later slices.
- Slice 2 look-up boundary: `afc/tool_model.py` (`lookup_models`) fetches only allow-listed public
  vendor doc URLs with `urllib`, an 8-second timeout, and no API key or auth header. The request
  carries no project code, secrets or paths. Any failure falls back to
  `~/.A-FC/model-options/<tool>.json`, then to local settings only; `AFC_MODEL_LOOKUP=off` skips
  the live fetch. `three_options` fills slots only with IDs a source returned, never invented ones.
  The cache is the only write, and it goes under `~/.A-FC/`, never the repo.
- One new module, `afc/tool_model.py`, reads which tool is running (from environment variables, the
  same way `afc/config.py` reads `CLAUDE_CODE_SESSION_ID`), the model the tool's settings show
  (per-tool reader keyed like `tool_coverage.TOOLS`: `cursor`, `codex`, `copilot`, `antigravity`),
  and builds options. A new `afc/cli_model.py` adds `model` (`--role`, `--options`) and
  `model choose <model>`, registered in `afc/cli.py` and `afc/cli_parser.py` the same way as
  `cli_agents`.
- Two paths for suggestions:
  - **Known model:** one optional switch from models that tool's settings already show (same as
    before).
  - **Don't know / not shown:** local settings (what is installed or listed) plus a short public
    look-up of what is current for that tool; merge into exactly three options — premium, best
    cost, hybrid — each with a one-line reason aimed at subscription users (which model fits heavy
    work, everyday work, or a middle path on the plan they already have). Prefer a model the local
    settings already list when it still fits a slot; otherwise use the look-up. Never invent a
    model ID that neither source returned. Never ask for or store an API key.
- The public look-up is read-only, timed, and fail-soft. On success it writes a cache under
  `~/.A-FC/model-options/` (per tool, with a `checked` timestamp). On failure it reads that cache
  if present; if not, it only uses models from local settings and says the look-up could not run.
  Flight Control's own repo never ships model version lists. Never send project code, secrets or
  paths in the look-up.
- The job's need for role-based asks still comes from FC-050's routing:
  `role_agents.resolve_model` → strong / balanced / light.
- The kept choice lives beside the routing in the workspace: `agents/routing.json` gains
  `tools.<tool>.model` and `tools.<tool>.seen`. A changed `seen` is what makes it ask again (A5).
  Missing `tools` keeps old files working.
- The ask goes where the session starts: one bullet in `afc/instructions.py` `PREFACE` (so
  `AGENTS.md` carries it after `sh bin/afc instructions --write`), and one line each in
  `afc-start` and `afc-slice`. `CLAUDE.md` changes only if the preface cannot carry it (A7).
- The health line extends `tool_coverage.lines`, not a new check, and never fails the check.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Read the tool and its model — you'll see it by `sh bin/afc model` run from a Cursor shell
      naming Cursor and the `modelId` from `~/.cursor/cli-config.json`, the same command naming Codex
      and its `config.toml` model under Codex's variable, "not shown" for Copilot, and the first five
      assumptions above ticked or struck (proves A1)
- [x] 2. Three options when they don't know — you'll see it by `sh bin/afc model --options` with no
      shown model returning exactly three options (premium, best cost, hybrid) whose names came from
      the look-up (or the machine cache), by a run with the look-up blocked using the cache or local
      settings only and saying so (never inventing IDs), and by a run with a shown light model and
      `--role architect` still offering a single switch when settings list a strong one (proves A2,
      A3; settles the look-up assumption)
- [ ] 3. Ask once and remember — you'll see it by a scratch project in Cursor whose first reply asks
      one question with three numbered answers when no model is shown (or two when one is),
      `model choose` writing `tools.cursor` in the scratch workspace's `agents/routing.json`, a
      second start asking 0 questions about the model, and a Claude Code start on the same project
      asking none (proves A4, A5, A7)
- [ ] 4. Ask again for the heavy jobs — you'll see it by an architecture request in Cursor on a
      light kept model asking once, a build request asking 0 times, and a second architecture request
      in the same session asking 0 times (proves A6)
- [ ] 5. Health line and live run — you'll see it by `sh bin/afc check` listing the shown and kept
      model on each tool's line, and the live Cursor "don't know" run's three options and choice
      written in Decisions (proves A8, A9)

## Tasks

Slice 1:
- `afc/tool_model.py` (new): `detect_tool()` from environment variables; `shown_model(tool)` with
  one reader per tool (Cursor `cli-config.json`, Codex `config.toml`, Copilot none, Antigravity per
  slice 1's finding); returns model, file and "not shown".
- `afc/cli_model.py` (new): `model` prints tool, model and where it came from.
- `afc/cli.py`, `afc/cli_parser.py`: register `cli_model`.
- `docs/architecture.md` (via `afc-architect`): a row for `tool_model.py` and `cli_model.py`.
- This spec: tick or strike the first five assumptions; fix the settings table.

Slice 2:
- `afc/tool_model.py`: `fit(model)` family-name rules (no version IDs); `need(role, routing)` from
  `role_agents.resolve_model`; `suggest(role, routing, shown)` for the single-switch path;
  `three_options(tool, shown)` merging local lists with a timed public look-up into premium / cost /
  hybrid; cache last successful look-up under `~/.A-FC/model-options/`.
- No model catalog file in the A-FC repo.
- `afc/cli_model.py`: `--role` and `--options` print the right shape with one-line reasons.

Slice 3:
- `afc/cli_model.py`: `model choose <model>` writes `tools.<tool>.model` and `.seen` to the active
  project's `agents/routing.json`; `model` says `ask: true` only when nothing is kept or `seen` has
  changed; when ask is true and nothing is shown, `options` holds the three choices.
- `afc/role_agents.py`: `load_routing` and `save_routing` keep a `tools` block untouched.
- `templates/workspace/agents/routing.json`: a note on `tools`.
- `afc/instructions.py` `PREFACE`: one bullet for the model ask (three options when they don't know).
  Then `sh bin/afc instructions --write`.
- `.claude/skills/afc-start/SKILL.md`: one line: the model question comes after the welcome's
  question is answered, never in the same message; use the three options when `options` is present.

Slice 4:
- `.claude/skills/afc-slice/SKILL.md`, `.claude/skills/afc-architecture/SKILL.md`: one line each:
  in a tool other than Claude Code, before architecture or spec planning, run
  `sh bin/afc model --role architect` (or `plan`) and ask once per session when it suggests a switch.
- `afc/cli_model.py`: `--role` says `ask: true` only for strong-need roles on a light kept model.

Slice 5:
- `afc/tool_coverage.py`: `coverage` and `lines` add the shown and kept model per tool.
- Live Cursor run on a scratch project (never a real one); write the three options, the choice and
  question counts in Decisions.

## Decisions

- 2026-10-27: In Cursor, ask and suggest a better fit from local settings. Chosen over keeping whatever
  model the project started with. The Claude Code warning stays in FC-050.
- 2026-10-27: Ask once per project per tool and keep the answer in the workspace routing file, asking
  again only when the tool's settings show a new model or a heavy job meets a light model. Chosen
  over asking every session, which would add a question to every start.
- 2026-10-27: When a model is already shown, prefer a single switch from that tool's own settings.
  When the user does not know (or nothing is shown), check local settings and a short public look-up,
  then offer exactly three options: top tier (premium), best for cost, and hybrid (quality and cost).
  Fail soft to a per-machine look-up cache or local settings only. Never write the tool's settings.
- 2026-10-27: Never ship model names or version IDs inside Flight Control. They go stale (a user next
  year would get outdated advice). Current names come only from the tool's settings, a live look-up,
  or a cache of a past look-up on that machine. Family rules (opus / sonnet / haiku-style words) may
  classify a name; they must not pin a concrete version.
- 2026-10-27: Most of these tools are used by subscription (in-app model picker), not by pasting an
  API key. Advice and the three options are framed for plan users; Flight Control never asks for an
  API key and never ranks by token price.

- 2026-10-27 slice 3 re-run (dev `dfe43d7`, scratch `AFC_HOME` only): Copilot with nothing shown —
  first `sh bin/afc model --tool copilot` returned `ask: true` and three `options` (premium / cost /
  hybrid) from the Copilot models doc; `model choose gpt-5-3-codex` wrote `tools.copilot` in the
  scratch workspace `agents/routing.json`; a second `model` returned `ask: false` with the same
  `kept`. Cursor with `CURSOR_AGENT=1` on a fresh scratch project — first `model` returned
  `ask: true` with `suggest` (two-answer path for `composer-2.5` shown); `model choose composer-2.5`
  wrote `tools.cursor` with `seen` `composer-2.5`; second `model` returned `ask: false`; `model
  --tool claude` on that project returned `ask: false` and `agents: sh bin/afc agents`. Not measured
  here: a live Cursor chat whose first reply asks the model question (that stays for slice 5).

## Shipped
