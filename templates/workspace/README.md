# Workspace planning templates

Flight Control copies these into `~/.A-FC/projects/<name>/plan/` when a project workspace is created.

| Area | Location | Purpose |
|---|---|---|
| Master plan | `plan/master-plan.md` | Goal, what's in progress, what's next, what's done, update log |
| Active specs | `plan/specs/` | One markdown file per piece of work not yet finished (`S-001-<slug>.md`, …) |
| Archive | `plan/archive/` | Finished spec files, `index.md` pointers, and rotated years of the update log and the Done table |
| Spec template | `templates/workspace/spec.md` (here in A-FC) | Starting shape for new specs; `plan add` fills this in later |

Supporting plan files (`intent.md`, `decisions.md`, `architecture.md`, `drift-notes.md`, `process-steps.md`)
stay beside the master plan. Move a spec into `archive/` only when every slice is approved and the work
is marked done — never delete finished specs.
