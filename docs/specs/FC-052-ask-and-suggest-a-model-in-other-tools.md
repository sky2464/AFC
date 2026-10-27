# FC-052 — Ask and suggest a model in other tools

Size: M · Status: next · Started: - · Done: -

## Goal

When Flight Control is used in a tool other than Claude Code, such as Cursor, it asks which model to
use and suggests a better fit when that tool's settings show one.

## Reaches the apps

## You'll know it works when

- A1. <what you will see when it works>

## Out of scope

Claude Code's own warning when something overrides the model set for each job. That stays in FC-050.

## Assumptions to confirm

- [ ] <a guess this spec rests on; tick it once slice 1 settles it>

## Design notes

## Slices

- [ ] 1. <label> — you'll see it by <how> (proves A1)

## Tasks

Slice 1:
- <file>: <what changes>

## Decisions

- 2026-10-27: In Cursor, ask and suggest a better fit from local settings. Chosen over keeping whatever
  model the project started with. The Claude Code warning stays in FC-050.

## Shipped
