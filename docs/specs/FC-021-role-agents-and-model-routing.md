# FC-021 — Role agents and model routing

Size: M · Status: next · Started: - · Done: -

Asked for on 2026-10-25, to split research, plan, build and check into dedicated helpers with an
explicit model per role instead of one default model for every helper.

## Goal

Flight Control defines four role agents — research, plan, build and check — each with a model in
agent frontmatter. The main co-pilot session never defaults to Haiku. Projects can override models
through a workspace `routing.json` without editing repo agent files.

## You'll know it works when

- Four agent files live under `.claude/agents/` (`afc-research`, `afc-plan`, `afc-build`,
  `afc-check`). Each frontmatter includes a `model` field.
- Defaults are research Haiku, plan Opus, build Sonnet, check Haiku, unless `routing.json` overrides
  a role for the active project.
- `sh bin/afc routing show` prints the resolved model per role for the active project (repo defaults
  plus overrides) as one JSON object.
- Workflows and skills that start a role helper pass `agentType` and do not hard-code a model when
  `routing.json` supplies one; the workflow still accepts explicit `builder` / `checker` args for
  maintenance builds and falls back to routing when omitted.
- Bedrock and Vertex deployments can set full provider model IDs in `routing.json` (documented in
  one place in the spec's Decisions or in `docs/` beside routing); a test fixture shows a Bedrock
  ID round-trips through `routing show` unchanged.
- When the resolved research or check model is Haiku 5.5 (`claude-haiku-4-5` or the documented
  alias), `sh bin/afc routing show` warns if Claude Code is older than v2.1.293; the main session
  model is never set to Haiku by default in session start or project profile.
- The full suite passes.

## Out of scope

Per-project install of copied agents (`FC-022`). Token and cost attribution (`FC-023`). Changing
which tools each role may use beyond what today's builder and checker already allow. Enterprise
policy that forbids certain providers (handled where profiles are enforced).

## Design notes

- **Roles.** Research gathers facts and reads code; plan drafts or updates plan text; build implements
  a slice; check runs tests and judges a slice. Names match `afc-*` like today's builder and checker.
- **Frontmatter.** YAML `model:` on each agent file is the repo default. Optional `description` and
  `tools` lists stay lean (same idea as `afc-builder` / `afc-checker`).
- **routing.json.** Lives in the project workspace (`~/.A-FC/<project>/routing.json`), keys
  `research`, `plan`, `build`, `check`, values are model strings. Missing keys use repo defaults.
  Invalid JSON or unknown keys are refused with a plain error from `routing show` and `routing set`.
- **Provider IDs.** Document that Bedrock and Vertex need the full ID the host expects (examples in
  Decisions when implemented), not only short Claude aliases.
- **Haiku 5.5.** Claude Code v2.1.293 is the floor for Haiku 5.5; the CLI reads `claude --version`
  or an env override used in tests.
- **Main session.** Session start and `afc-profile` never assign Haiku as the default main model;
  role helpers may still use Haiku for research and check.

## Slices

- [ ] 1. Routing resolution — you'll check it by `tests/test_routing.py`: repo defaults
      Haiku/Opus/Sonnet/Haiku, overrides per role from a temp workspace `routing.json`, Bedrock ID
      preserved, bad JSON refused, Haiku 5.5 warning when version is below 2.1.293 (tests)
- [ ] 2. Four role agents — you'll check it by the four files under `.claude/agents/` each naming
      `model` in frontmatter with the defaults above, and a structural test that main session hooks
      do not set Haiku as the default model
- [ ] 3. `sh bin/afc routing show|set` — you'll check it by CLI tests: `show` merges defaults and
      overrides, `set research <model>` writes `routing.json` under the active project workspace
      (tests)
- [ ] 4. Workflows use routing — you'll check it by `afc-build-spec.js` (and any other workflow that
      names builder/checker) resolving models from routing when args omit them, with an existing
      explicit arg still winning; one structural test on the workflow source

## Decisions

- 2026-10-25: Default models are research Haiku, plan Opus, build Sonnet, check Haiku; main session
  stays off Haiku.

## Shipped
