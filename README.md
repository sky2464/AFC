<div align="center">

# ✈️ Flight Control

### Your AI architect, project manager and security officer in one.

Spec-driven from day one: Flight Control locks onto your goal, keeps every step on course,<br>
and delivers a working app.

[![Version](https://img.shields.io/badge/version-0.02a_alpha-orange)](https://github.com/sky2464/AFC/releases/tag/v0.02a)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Runs in Claude Code](https://img.shields.io/badge/runs_in-Claude_Code-d97757)](https://claude.com/claude-code)
[![Platforms](https://img.shields.io/badge/macOS_·_Linux_·_Windows-lightgrey)](#questions)

[Get started](#get-started) · [Why Flight Control](#why-flight-control) · [How a session goes](#how-a-session-goes) · [Your work stays yours](#your-work-stays-yours) · [Safety](#safety) · [Questions](#questions)

</div>

---

## Why Flight Control

You describe what you want. Flight Control turns it into a clear plan and builds it one small,
working piece at a time, and you approve each piece once you've seen it work.

| | |
|---|---|
| 🧭 **Spec-driven** | Works out what you really want, one question at a time, before anything is built. |
| 🎯 **Stays on your goal** | Notices when work drifts from what you agreed and brings it back on course. |
| 🏗️ **Thinks like an architect** | Remembers how your project fits together and checks the impact of every change. |
| 🛡️ **Security built in** | Checks every file change and command, and blocks secrets, risky git commands and accidental publishing. |
| 🧑‍✈️ **Runs the project** | Plans, builds, tests and saves your work. You decide what to build and approve what works. |
| 🙂 **Simple by design** | No commands to learn. Every reply ends with at most two clear next steps. |

## Get started

**You need** [Claude Code](https://claude.com/claude-code), git, and Python 3.10 or newer.
No Python yet? Start anyway: Flight Control notices, tells you in one line, and offers to install it,
only after you say yes.

**1. Get Flight Control**

```bash
git clone --depth 1 https://github.com/sky2464/AFC.git A-FC
```

**2. Open it in Claude Code**

```bash
cd A-FC
```

```bash
claude
```

**3. Answer the welcome**

```
✈️  Flight Control — your AI architect, project manager and security officer in one.
Spec-driven from day one: locks onto your goal, keeps every step on course, delivers a working app.
Type 1 to start a new project, 2 to bring in one already on this computer, or just say hi.
```

That's it. You never update by hand. When a newer release is out, the welcome says so in one line
and offers **1. Update now** or **2. Not now**. Update now brings you to the latest release and tells you
what changed. Not now stays quiet until an even newer release comes out. If the update changes
something Flight Control only reads when a session starts, it asks you to type `/exit` and reopen
with `claude --continue` in the `A-FC` folder, which picks up the same conversation. If the update
can't be applied safely (you edited files in the folder, or it's on another branch), nothing is
changed and Flight Control tells you why.

Copies on v0.02a or older have no updater: update them once with `git pull` in the `A-FC` folder. From v0.03a on,
Flight Control offers updates itself.

## How a session goes

1. **You say what you want to build.** Flight Control asks one question at a time until the goal is
   clear: who it's for, what "done" looks like, what to leave out.
2. **It plans the first small piece**, something you can actually see or run.
3. **It builds and checks it**, with tests, and shows you the result.
4. **You decide.** "Yes, that's it" saves the piece and moves to the next one; "not quite" changes
   course before anything grows on top of it.

Flight Control keeps a master plan of small specs and moves finished ones to an archive in your private workspace.

Lost track? Type `/afc` any time to see where you are and what's next. It's the only command there is.

## Your work stays yours

Flight Control keeps three things apart, so nothing gets mixed up:

| Where | What's there |
|---|---|
| 📁 **Your app's folder** | Your app's code and tests, nothing else. |
| 🔒 **`~/.A-FC/`** | A private workspace per project: plans, decisions, notes and reports. It stays on your computer and is never put in a repo. |
| ✈️ **The `A-FC` folder** | Flight Control itself. Updating it never touches your work. |

## Safety

**Always enforced.** Before every file change and command, Flight Control checks it, and when in
doubt it blocks:

- ✋ changes outside the project you're working on;
- 🔑 anything that looks like a password, key or token;
- 🏢 copying company material into an app's code (this also means backups of `~/.A-FC/` happen
  from your own terminal, not from inside Claude);
- ⚠️ git commands that lose work or rewrite history, like force-push or `reset --hard`;
- 🌍 making anything public; new repositories are private.

**Always yours to do.** Making a repo public, force-pushing, deleting branches, merging other people's
work and deploying to production. Flight Control explains the steps; you take them. It drafts emails
and forms but never sends them.

**Good to know.** Commands are checked as text, so an unusual spelling can slip through. The checks
catch accidents by a cooperative AI; they are not a defense against a hostile one.

## Role agents and models (optional tuning)

New projects get four helpers in the app's `.claude/agents/` folder — research, plan, build and
check — with default models aimed at **faster, cheaper research and checks** and **stronger planning
and building**. The main chat session is not put on Haiku.

Overrides live in the private workspace at `agents/routing.json` (never in the app repo). Run
`sh bin/afc agents` to see resolved models; `sh bin/afc agents sync` after you edit routing.
`resources/afc-brief.md` is a short project memory refreshed on setup and after each deliver — read
it once per slice instead of reloading every plan file.

TypeSafe Jev is **off by default** and not wired into reviews yet; see `docs/specs/FC-024-optional-jev.md`
if you want the stub adapter. Measuring cost from a Claude Code transcript:
`python3 docs/measurements/token_usage.py <transcript.jsonl>` now includes a rough `estimated_cost_usd`.

## Questions

**Do I need to know how to code?**
No. You describe what you want and approve what works. Knowing some code helps you judge the details,
but the questions are in plain language.

**Which computers does it run on?**
macOS, Linux and Windows (with Git Bash, which Claude Code uses on Windows). This alpha has been
tested on macOS; Linux and Windows are supported but not yet tried on real machines.

**What does it cost?**
Flight Control is free. It runs inside Claude Code, which needs a Claude plan or an Anthropic API key.

**Where is my data?**
Your code stays in your app's folder and your plans stay in `~/.A-FC/` on your computer. Flight
Control adds no services of its own; Claude Code talks to Claude as it always does.

**Can I bring in a project I already have?**
Yes. Type 2 at the welcome and point it at the folder.

**Why are some of my add-ons off in Flight Control?**
Flight Control only loads the add-ons on its allowed list (`afc-addons.json`), so a broken add-on
can't spoil a session. They still work everywhere else; `/afc` → More… → Health check explains each one.

**Something isn't working.**
Please [open an issue](https://github.com/sky2464/AFC/issues) and say what you typed and what you saw.

---

<div align="center">
<sub>Want to help build Flight Control, or keep a second copy for trying things out? See
<a href="CONTRIBUTING.md">CONTRIBUTING.md</a> — a second copy needs a workspace of its own, or it
writes into this one's.</sub>

<sub>Licensed under the <a href="LICENSE">MIT License</a>.</sub>
</div>
