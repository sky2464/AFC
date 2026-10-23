# Flight Control

**Your AI architect, project manager and security officer in one.** Spec-driven from day one: Flight
Control locks onto your goal, keeps every step on course, and delivers a working app.

It runs inside [Claude Code](https://claude.com/claude-code). You say what you want to build; it works
out the details with you one question at a time, then builds one small piece you can see or run, asks
"is this what you meant?", and repeats, with security and architecture practice built in.

> **Status: alpha ([v0.01a](https://github.com/sky2464/AFC/releases/tag/v0.01a)).** Tested on macOS.
> Windows (Git Bash) and Linux are supported but not yet tried on real machines.

## Get started

**You need:** Claude Code, git, and Python 3.10 or newer. No Python yet? Start anyway: Flight Control
notices, tells you in one line, and offers to install it, only after you say yes.

1. Download Flight Control into a folder of its own:

   ```bash
   git clone --depth 1 https://github.com/sky2464/AFC.git A-FC
   ```

2. Open it in Claude Code:

   ```bash
   cd A-FC
   ```

   ```bash
   claude
   ```

3. Answer the welcome:

   ```
   ✈️  Flight Control — your AI architect, project manager and security officer in one.
   Spec-driven from day one: locks onto your goal, keeps every step on course, delivers a working app.
   Type 1 to start a new project, 2 to bring in one already on this computer, or just say hi.
   ```

From there, just talk. Every reply ends with at most two numbered next steps, so you always know what
to do. `/afc` is the only command to remember: it shows where you are and what's next.

**Updating:** run `git pull` inside the `A-FC` folder.

## How it works

Flight Control keeps three things apart:

| Place | What is in it | Shared? |
|---|---|---|
| `A-FC/` (this folder) | The brain only: instructions, skills, the `/afc` command, safety checks, rules, templates | Yes |
| `~/.A-FC/` (or `$AFC_HOME`) | One private workspace per project (plan, resources, reports, index) and your project list | Never, it stays on your computer |
| Your app's own folder | Code and tests only | Per that project |

This folder never holds your project data, so updating Flight Control never touches your work.

## Safety

**Always enforced (checked before every file change and command; when in doubt they block):**
- Writes outside the active project (and its workspace) are blocked.
- Writes to Flight Control itself are blocked unless maintenance mode is on.
- Likely secrets (keys, tokens, password/api_key/token assignments, quoted or `.env`-style) are blocked.
- Company resources cannot be copied into an app repo. This also means copying or backing up
  `~/.A-FC/` to another folder from inside a Claude session is blocked: do backups from your own
  terminal.
- Git commands that lose work or rewrite history (`reset --hard`, `clean -f`, `branch -D`, force
  push…) are blocked.
- Making anything public (e.g. `gh repo create --public`) is blocked; new remotes are private.

**Guided (Claude follows these instructions; nothing forces it):** the one-question interview, slice
size, drift checks, live docs, scans before delivery, drafting (never sending) emails and forms, the
two-step reply style.

**Limits.** Command checks are best effort: commands are read as text, so an unusual spelling can slip
through. The checks protect against accidents by a cooperative AI, not against a hostile one.

## For developers

Work on Flight Control itself in a full clone, not in the folder you use day to day:

```bash
git clone https://github.com/sky2464/AFC.git A-FC-dev
```

- **Branches:** `main` holds released versions (tagged, e.g. `v0.01a`); ongoing work happens on `dev`.
- **Tests** always use a temporary `AFC_HOME`, so they never touch your real `~/.A-FC`:

  ```bash
  python3 -m unittest discover -s tests -v
  ```

- **Editing:** the safety checks block edits to Flight Control by default. Turn on maintenance mode
  with `sh bin/afc maintain on` (or `/afc` → More…), and turn it off with `sh bin/afc maintain off`
  when done.
- **Design:** see `docs/superpowers/specs/2026-10-21-flight-control-design.md` and the acceptance
  results in `docs/superpowers/acceptance/`.
