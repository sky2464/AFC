# Master plan

Flight Control's own master plan, kept in the same shape it gives every project. Specs live in
`docs/specs/`; finished ones move to `docs/specs/archive/`. Build each spec on `dev`, one commit
per slice, with maintenance mode on while editing.

## Goal

A calm co-pilot inside Claude Code or well known Agentic AI code developments that turns what someone wants to build into small, working,
dynamic, smart safe slices, with as clarity questions and as little noise as possible.

Every change must reach the apps Flight Control builds for users.

## Now

| ID | Title | Size | Spec | Started |
|---|---|---|---|---|

## Next

| ID | Title | Size | Spec |
|---|---|---|---|
| FC-052 | Ask and suggest a model in other tools | M | [spec](specs/FC-052-ask-and-suggest-a-model-in-other-tools.md) |


## Waiting on you

| # | Step | Added |
|---|---|---|

## Done

| ID | Title | Done | Spec | Release | Outcome |
|---|---|---|---|---|---|
| FC-051 | Flight Control works in other AI tools | 2026-10-27 | [FC-051](specs/archive/FC-051-flight-control-works-in-other-ai-tools.md) |  |  |
| FC-050 | Right model for each job | 2026-10-27 | [FC-050](specs/archive/FC-050-right-model-for-each-job.md) |  |  |
| FC-049 | Architecture memory for Flight Control | 2026-10-26 | [FC-049](specs/archive/FC-049-architecture-memory-for-flight-control.md) |  |  |
| FC-046 | Findings, parked and waiting in one place | 2026-10-26 | [FC-046](specs/archive/FC-046-findings-parked-and-waiting-in-one-place.md) |  |  |
| FC-047 | Apps close out cleanly, and a lean log | 2026-10-26 | [FC-047](specs/archive/FC-047-apps-close-out-cleanly-and-a-lean-log.md) |  |  |
| FC-045 | Releases and results from the plan | 2026-10-26 | [FC-045](specs/archive/FC-045-releases-and-results-from-the-plan.md) |  |  |
| FC-044 | The plan can't drift | 2026-10-26 | [FC-044](specs/archive/FC-044-the-plan-can-t-drift.md) |  |  |
| FC-048 | MM: prefix turns maintenance mode on | 2026-10-26 | [FC-048](specs/archive/FC-048-mm-prefix-turns-maintenance-mode-on.md) |  |  |
| FC-043 | Ready means ready | 2026-10-26 | [FC-043](specs/archive/FC-043-ready-means-ready.md) |  |  |
| FC-040 | Ready for v0.06a | 2026-10-26 | [FC-040](specs/archive/FC-040-ready-for-v0-06a.md) |  |  |

## Areas

Where the work is going. Each spec names its area so nothing drifts.

| Area | Target | Scoreboard |
|---|---|---|
| flow | first start < 50k tokens; zero questions before the first slice | First-start tokens |
| tokens | < 0.15M tokens per slice | Tokens per slice |
| safety | guards catch all known failure modes; no secrets in files | — |
| updates | self-update in < 60 s with no manual steps | — |

## Scoreboard

| Measure | Now | Before | Source |
|---|---|---|---|
| First-start tokens | 56,247 | 73,310 | FC-038 |
| Tokens per slice | 0.25M | 7.5M | FC-018 |
| Full-suite runs per slice | 5.0 | 8.7 | FC-018 |

## Findings

Findings: none open. Full list and history in [docs/findings.md](findings.md).

## Update log

| Date | Event |
|---|---|
| 2026-10-24 | FC-016 specced and sliced (3 slices): compaction drops Done rows instead of archiving them, which lost the PC and v0.01a rows; FC-015 depends on it |
| 2026-10-25 | FC-009 closed: slice 4 measured at 46,010 growth against 24,490, target not met; spec archived |
| 2026-10-25 | FC-012 slice 3 approved and ticked: the health check sees the A-FC folder; spec stays in Next while FC-009 holds Now |
| 2026-10-25 | FC-014 slice 1 approved and ticked: review gives a verdict; spec stays in Next while FC-009 holds Now |
| 2026-10-25 | FC-018 done: helpers 7.0→2.0 and tokens 7.5M→0.25M per slice, full-suite runs 8.7→5.0 (target 4.35 missed; FC-013 run-one-file rule covers it) |
| 2026-10-25 | FC-027 renamed to Add-ons off at start, quiet health check |
| 2026-10-26 | waiting: R6: move A-FC-test to current code (973da0c is stale) |
| 2026-10-26 | waiting: FC-040 release: make the v0.06a tag, push it, and publish re |
