# Reference: the earlier Flight Control build

Kept for reference only. Nothing here describes how Flight Control works today.

These three notes come from an earlier, separate build of Flight Control (TypeScript on Bun, set up as
a Claude Code plugin; worked on 2026-10-15 to 2026-10-17, 78 commits). That build was set aside; the
current Flight Control is the Python one in this repository. The old repository was removed after
these notes were copied out.

| Note | What it holds | Why it is still worth reading |
|---|---|---|
| [vision-v2.md](vision-v2.md) | The original vision: a brain folder that manages many projects, one-way access to the code folder, you approve every spec, the before/during/after loop | The intent behind today's design, in the founder's own words |
| [spike-results.md](spike-results.md) | What was observed in Claude Code 2.1.300: where instructions load from, plugin command names, hook behaviour (including for subagents), when `--add-dir` allows writes | Facts about Claude Code that the guards and hooks here still depend on. Re-check them before relying on them: the version is old |
| [build-notes.md](build-notes.md) | The open items, rulings and residual risks from building the shell-command guard | A ready list of the ways a shell guard is bypassed, useful when changing `afc/hooks` or the guard-command tests |

Left behind on purpose: the 31,000-word implementation plan and the two design specs, which describe code
that no longer exists.
