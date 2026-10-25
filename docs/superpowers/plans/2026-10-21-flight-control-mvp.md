# Flight Control MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `A-FC` folder into Flight Control: a Claude Code "brain" that manages external projects slice by slice, keeps their plans in a private `~/.A-FC` workspace, and hard-enforces security rules with tested hooks.

**Architecture:** Two layers. (1) A small stdlib-only Python package `afc/` holds everything that must be deterministic and tested: registry, workspace, profiling, hook guards, scans, git decisions, graph wrapper — exposed as `python3 -m afc <command>` and as hook entry points. (2) Markdown instructions (`CLAUDE.md`, `.claude/skills/afc-*`, `.claude/commands/afc-*`, `rules/*.md`, `templates/`) hold the judgment work — interview, slices, drift, enterprise guidance — and call the CLI for anything mechanical.

**Tech Stack:** Claude Code (CLAUDE.md, skills, commands, hooks in `.claude/settings.json`), Python 3.14 standard library only, `unittest`, git, `gh` (GitHub), `az` (Azure DevOps, optional). No third-party graph tool.

**Spec:** `docs/superpowers/specs/2026-10-21-flight-control-design.md` (read it before any task).

## Global Constraints

- Claude Code only for the MVP; no other AI tool adapters.
- Python standard library only; no third-party packages in `afc/` or `tests/`. Tests run with `python3 -m unittest discover -s tests -v` from the A-FC root.
- Workspace root: `~/.A-FC/`, overridable by env `AFC_HOME`. Tests always set `AFC_HOME` to a temp dir.
- The A-FC repo never contains project data (no workspace content, no company resources, no project paths in tracked files).
- **Own naming only:** every folder/file Flight Control creates uses its own names; no third-party tool names (e.g. `graphify-out/`) appear in the app repo, the workspace, or A-FC markdown.
- Hook input is JSON on stdin; exit code 2 + stderr blocks a tool call; exit 0 allows. Every hard rule has a unit test proving it blocks.
- Guards fail **closed**: unreadable input or an internal error exits 2 with a readable reason.
- New remote repos are **private by default**; making anything public is always blocked by the guard and requires the user.
- Flight Control drafts emails/forms; it never sends them.
- Third-party skills/MCP servers are installed only on the user's explicit yes.
- No file in A-FC exceeds 500 lines.
- **Simple by default (user decision):** one visible command, `/afc`; every Flight Control reply ends with at most two numbered next steps, recommended first; skills, CLI and workflows are internal and never listed unless asked.
- Use `pathlib` everywhere (Windows support later).
- A-FC commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

- **Storage (user decision):** files are the truth; SQLite (`index.db` per workspace + `~/.A-FC/index.db`) is a rebuildable index, never inside an app repo; the cross-project index never contains company resources.

## Review Focus

1. **Path forms:** `~`, spaces, trailing slashes, relative paths in `tool_input`, and macOS `/tmp` vs `/private/tmp` symlinks must be resolved before allow/deny — a write to `./src/x.py` with cwd inside the active code path is allowed; `../other/x.py` escaping it is blocked. → Task 5 tests `test_relative_path_resolved_against_cwd`, `test_escape_with_dotdot_blocked`, `test_tmp_symlink_allowed`.
2. **Malformed hook input:** empty stdin, non-JSON, missing `tool_input`, or an unknown tool must never crash open; write tools are denied with a readable reason, unknown tools pass. → Task 5 tests `test_empty_stdin_blocks`, `test_unknown_tool_allowed`.
3. **Placeholder secrets:** `your-api-key-here`, `${API_KEY}`, `process.env.API_KEY`, `os.environ["X"]`, `<token>` must not be blocked; real-looking keys must be. → Task 6 `test_placeholders_not_flagged`.
4. **No/corrupt registry:** first-ever run, missing `projects.json`, or corrupted JSON must still show the welcome and give a clear message instead of a stack trace; guards block writes outside `AFC_HOME` with "pick a project — type /afc". → Task 2 `test_corrupt_registry_raises_clear_error`, Task 9 `test_welcome_with_corrupt_registry`.
5. **Unsafe project names / existing folders:** `../x`, `My App`, names over 63 chars, or a non-empty existing target folder on `new` are rejected with a message. → Task 2 `test_invalid_names_rejected`, Task 4 `test_new_refuses_non_empty_folder`.

---

## File Structure

```
A-FC/
  CLAUDE.md                         brain entry: role, three places, routing, hard rules (≤150 lines)
  README.md                         what Flight Control is, how to start, how to run tests
  .gitignore
  .claude/settings.json             hook wiring (SessionStart, PreToolUse)
  .claude/commands/afc.md           the only visible command: where you are + 1–2 next steps; "More…"
  .claude/skills/afc-start/SKILL.md          launch, new, existing, returning (§7)
  .claude/skills/afc-interview/SKILL.md      intent, research, interview, profiling (§8.1, §10.1)
  .claude/skills/afc-slice/SKILL.md          slice loop + 3 checkpoints + live docs (§8.2, §8.4, §10.3)
  .claude/skills/afc-drift/SKILL.md          intent + code drift (§8.3)
  .claude/skills/afc-deliver/SKILL.md        commit/push/PR/remote (§9)
  .claude/skills/afc-enterprise/SKILL.md     wiki lookups, resources, people-side steps (§10.1, §10.4)
  .claude/skills/afc-architecture/SKILL.md   architecture memory + graph (§11)
  .claude/skills/afc-capabilities/SKILL.md   discovery, vetting, skill writing, promotion gate (§12)
  rules/secrets.md identity.md input.md api.md logging-pii.md dependencies.md
        containers-deploy.md data.md architecture.md ai-safety.md
  templates/workspace/plan/intent.md decisions.md progress.md drift-notes.md architecture.md process-steps.md
  templates/app/README.md  templates/app/gitignore
  library/skills/.gitkeep           reusable skills promoted from projects
  afc/__init__.py  __main__.py
  afc/config.py                     afc_home, afc_root, maintain flag
  afc/registry.py                   Project, Registry, load/save, name validation
  afc/workspace.py                  create_workspace
  afc/profile.py                    classify, modules_for
  afc/session_dirs.py               grant_dirs (settings.local.json)
  afc/cli.py                        argparse commands
  afc/secrets.py                    find_secrets (shared by guard and scan)
  afc/fingerprint.py                resource fingerprints
  afc/scan.py                       slice checks + report
  afc/git_ops.py                    delivery decisions + git/gh/az wrappers
  afc/codegraph.py                  own code graph extractor (stdlib)
  afc/index.py                      rebuildable SQLite index (per project + cross-project)
  afc/hooks/__init__.py common.py rules_paths.py rules_secrets.py rules_resources.py rules_git.py
  afc/hooks/pretool.py  session_start.py
  tests/helpers.py  test_*.py (one per module)  tests/fixtures/
```

---

### Task 1: Repository foundation and config

**Files:**
- Create: `.gitignore`, `README.md` (stub: title + "run tests" line), `afc/__init__.py`, `afc/__main__.py`, `afc/config.py`, `afc/hooks/__init__.py`, `library/skills/.gitkeep`, `tests/__init__.py`, `tests/helpers.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `afc_home() -> Path` (env `AFC_HOME` else `~/.A-FC`, expanded + resolved, need not exist); `afc_root() -> Path` (repo root, from `__file__`); `maintain_enabled(home: Path) -> bool` (file `home/"maintain"` exists); `set_maintain(home: Path, on: bool) -> None`.
- Produces (tests): `tests/helpers.py` → `class AfcTestCase(unittest.TestCase)` whose `setUp` creates `self.home` (temp dir, set as `AFC_HOME`) and `self.tmp` (scratch dir), and `tearDown` restores env and removes both. `make_event(tool_name: str, tool_input: dict, cwd: Path) -> str` returns hook JSON; `ev(tool_name: str, tool_input: dict, cwd: Path | None = None) -> dict` and `bash(command: str, cwd: Path | None = None) -> dict` return the same event as a dict (cwd defaults to `/`); `fixture(name: str) -> str` reads `tests/fixtures/<name>`; `run_cli(argv: list[str]) -> tuple[int, dict]` calls `afc.cli.main` with captured stdout parsed as JSON.

- [ ] **Step 1:** `git init -b main` in A-FC. `.gitignore` contains: `__pycache__/`, `*.pyc`, `.DS_Store`, `.claude/settings.local.json`, `.remember/`.
- [ ] **Step 2: Write failing tests** `tests/test_config.py`:

```python
class ConfigTest(AfcTestCase):
    def test_home_from_env(self):
        self.assertEqual(afc_home(), self.home.resolve())
    def test_home_default(self):
        del os.environ["AFC_HOME"]
        self.assertEqual(afc_home(), (Path.home() / ".A-FC").resolve())
    def test_root_contains_claude_md_dir(self):
        self.assertTrue((afc_root() / "afc" / "config.py").exists())
    def test_maintain_toggle(self):
        self.assertFalse(maintain_enabled(self.home))
        set_maintain(self.home, True);  self.assertTrue(maintain_enabled(self.home))
        set_maintain(self.home, False); self.assertFalse(maintain_enabled(self.home))
```

- [ ] **Step 3:** Run `python3 -m unittest tests.test_config -v` → FAIL (import error).
- [ ] **Step 4:** Implement `afc/config.py`, `tests/helpers.py`, empty `__init__.py` files; `afc/__main__.py` calls `sys.exit(cli.main(sys.argv[1:]))` (cli arrives in Task 4 — until then guard the import so the test run passes).
- [ ] **Step 5:** Run `python3 -m unittest discover -s tests -v` → PASS.
- [ ] **Step 6:** Commit, including the already-written `docs/superpowers/` design and plan:

```bash
git add -A && git commit -m "chore: initialize Flight Control repo and config"
```

---

### Task 2: Registry, project names, workspace

**Files:**
- Create: `afc/registry.py`, `afc/workspace.py`, `templates/workspace/plan/{intent,decisions,progress,drift-notes,architecture,process-steps}.md` (headings only for now; content in Task 15), `tests/test_registry.py`, `tests/test_workspace.py`

**Interfaces:**
- Consumes: `afc_home`, `afc_root` (Task 1).
- Produces:
  - `@dataclass Project`: `name: str`, `code_path: str`, `workspace_path: str`, `profile: str = "unknown"`, `status: str = "active"`, `last_active: str = ""`, `last_slice: str = ""`, `git_name: str = ""`, `git_email: str = ""`, `ai_trailer: bool = False`, `team_mode: str = "unknown"` (`solo|team|unknown`), `remote: str = "none"` (`none|github|azure`).
  - `class RegistryError(Exception)`.
  - `validate_name(name: str) -> str` — must match `^[a-z0-9][a-z0-9-]{1,62}$`, else `RegistryError`.
  - `class Registry`: `projects: dict[str, Project]`, `active_name: str | None`; methods `add(p: Project) -> None` (duplicate → `RegistryError`), `get(name) -> Project | None`, `set_active(name) -> None` (unknown → `RegistryError`), `active() -> Project | None`, `update(name, **fields) -> Project`.
  - `load_registry(home: Path) -> Registry` (missing file → empty registry; unreadable JSON → `RegistryError` whose message starts `projects.json is unreadable`).
  - `save_registry(home: Path, reg: Registry) -> None` — writes `home/projects.json` atomically (temp file + `os.replace`) **and** renders `home/projects.md` (a table: name, profile, status, last active, code path). *Plan call:* JSON is the machine source; `projects.md` is the human view the spec names.
  - `WORKSPACE_DIRS = ("plan", "resources", "reports", "skills")`; `create_workspace(home: Path, name: str) -> Path` creates `home/projects/<name>/` with those dirs and copies `templates/workspace/plan/*.md` without overwriting existing files.

- [ ] **Step 1: Write failing tests**

```python
def test_invalid_names_rejected(self):
    for bad in ["../x", "My App", "a", "x" * 64, "-lead", "kong_lab"]:
        with self.assertRaises(RegistryError): validate_name(bad)
    self.assertEqual(validate_name("kong-gateway-lab"), "kong-gateway-lab")
def test_round_trip_and_active(self):
    reg = load_registry(self.home)
    reg.add(Project("kong-gateway-lab", "/c/k", "/w/k")); reg.set_active("kong-gateway-lab")
    save_registry(self.home, reg)
    again = load_registry(self.home)
    self.assertEqual(again.active().code_path, "/c/k")
    self.assertIn("kong-gateway-lab", (self.home / "projects.md").read_text())
def test_duplicate_add_rejected(self): ...           # second add of same name → RegistryError
def test_corrupt_registry_raises_clear_error(self):
    (self.home / "projects.json").write_text("{not json")
    with self.assertRaisesRegex(RegistryError, "^projects.json is unreadable"): load_registry(self.home)
def test_workspace_layout(self):
    ws = create_workspace(self.home, "kong-gateway-lab")
    self.assertEqual(sorted(p.name for p in ws.iterdir()), sorted(WORKSPACE_DIRS))
    self.assertTrue((ws / "plan" / "intent.md").exists())
def test_workspace_does_not_overwrite(self): ...    # edit intent.md, call again, content kept
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_registry tests.test_workspace -v` → FAIL.
- [ ] **Step 3:** Implement `afc/registry.py` and `afc/workspace.py` with the signatures above.
- [ ] **Step 4:** Run the same command → PASS.
- [ ] **Step 5:** Commit `feat: add project registry and workspace creation`.

---

### Task 3: Project profile and rule-module selection

**Files:**
- Create: `afc/profile.py`, `tests/test_profile.py`

**Interfaces:**
- Produces:
  - `PROFILES = ("personal", "prototype", "mvp", "work", "enterprise")`
  - `ALL_MODULES = ("secrets", "identity", "input", "api", "logging-pii", "dependencies", "containers-deploy", "data", "architecture", "ai-safety")` — canonical order; also the file names in `rules/`.
  - `@dataclass Answers`: `purpose: str` (`learning|personal|prototype|mvp|work|product`), `users: int`, `audience: str` (`self|internal|external|both`), `company: str | None`, `sensitive_data: bool`.
  - `classify(a: Answers) -> str` — first match wins: company and (audience in `external|both` or `users > 50` or `sensitive_data`) → `enterprise`; company → `work`; purpose in `mvp|product` → `mvp`; purpose `prototype` → `prototype`; else `personal`.
  - `BASE_MODULES: dict[str, tuple[str, ...]]` — personal: `secrets, input, ai-safety`; prototype: + `dependencies`; mvp: + `api, logging-pii, architecture`; work: + `identity, data, containers-deploy`; enterprise: all of `ALL_MODULES`.
  - `TOUCH_MAP = {"auth": "identity", "api": "api", "data": "data", "deploy": "containers-deploy", "logs": "logging-pii", "deps": "dependencies", "input": "input"}`
  - `modules_for(profile: str, touches: set[str]) -> list[str]` — base ∪ mapped touches, returned in `ALL_MODULES` order; unknown profile → `ValueError`; unknown touch → ignored.

- [ ] **Step 1: Write failing tests**

```python
def test_kong_learning_is_personal(self):
    self.assertEqual(classify(Answers("learning", 1, "self", None, False)), "personal")
def test_internal_200_users_is_enterprise(self):
    self.assertEqual(classify(Answers("work", 200, "internal", "Acme", False)), "enterprise")
def test_small_internal_tool_is_work(self):
    self.assertEqual(classify(Answers("work", 10, "internal", "Acme", False)), "work")
def test_sensitive_data_escalates(self):
    self.assertEqual(classify(Answers("work", 5, "internal", "Acme", True)), "enterprise")
def test_product_without_company_is_mvp(self):
    self.assertEqual(classify(Answers("product", 1000, "external", None, False)), "mvp")
def test_modules_personal_touching_auth(self):
    self.assertEqual(modules_for("personal", {"auth"}), ["secrets", "identity", "input", "ai-safety"])
def test_enterprise_gets_all(self):
    self.assertEqual(modules_for("enterprise", set()), list(ALL_MODULES))
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_profile -v` → FAIL.
- [ ] **Step 3:** Implement `afc/profile.py`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add project profiling and rule-module selection`.

---

### Task 4: CLI — new, adopt, switch, list, status, open, maintain, modules, set

**Files:**
- Create: `afc/cli.py`, `afc/session_dirs.py`, `templates/app/README.md` (`# {name}` + one line), `templates/app/gitignore` (common ignores: `.env`, `.env.*` except `.env.example`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `.DS_Store`), `tests/test_cli.py`, `tests/test_session_dirs.py`
- Modify: `afc/__main__.py` (drop the import guard)

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: `main(argv: list[str]) -> int`. Every command prints one JSON object to stdout on success (exit 0) or `{"error": "<message>"}` (exit 1). Commands:
  - `new --name N --parent P --git-name G --git-email E [--ai-trailer] [--profile X]` → creates `P/N` (refuse if exists and non-empty), runs `git init -b main`, writes `README.md` and `.gitignore` from `templates/app/`, creates workspace, registers + activates, calls `grant_dirs`. Output keys: `project, code_path, workspace_path, granted`.
  - `adopt --name N --path P [--git-name G --git-email E]` → registers an existing folder (must exist); `is_git` in output.
  - `switch N`, `list`, `status` (active project fields + `now`: text under `## Now` in its `plan/progress.md`), `open` (macOS: `open <workspace>`; elsewhere just prints the path), `maintain on|off|status`, `modules --touches a,b` (uses active project's profile), `set FIELD VALUE` (fields: `profile, team_mode, remote, last_slice, git_name, git_email, ai_trailer`; validated against allowed values). Setting `profile` to `work` or `enterprise` adds `"warning"` to the output when `icloud_synced(code_path)` is true.
  - `icloud_synced(path: Path) -> bool` in `afc/cli.py` — true when `path` is under `~/Library/Mobile Documents/`, or under `~/Documents` / `~/Desktop` while `~/Library/Mobile Documents/com~apple~CloudDocs/Documents` exists (Desktop & Documents sync on). `new` and `adopt` include `icloud_synced` in their output.
  - `grant_dirs(root: Path, dirs: list[Path]) -> list[str]` in `afc/session_dirs.py` — merges resolved dirs into `root/.claude/settings.local.json` → `permissions.additionalDirectories` (dedupe, preserve other keys, create file if absent); returns the full list.

- [ ] **Step 1: Write failing tests** (call `main([...])` with `afc_root` patched to `self.tmp/"root"` for settings writes):

```python
def test_new_creates_everything(self):
    rc, out = run_cli(["new", "--name", "kong-gateway-lab", "--parent", str(self.tmp),
                       "--git-name", "Sky", "--git-email", "s@example.com"])
    self.assertEqual(rc, 0)
    code = Path(out["code_path"])
    self.assertTrue((code / ".git").is_dir() and (code / "README.md").exists())
    self.assertFalse((code / "graph").exists())          # nothing of ours leaks into the app repo
    self.assertEqual(load_registry(self.home).active().name, "kong-gateway-lab")
    self.assertIn(str(code), out["granted"])
def test_new_refuses_non_empty_folder(self): ...         # pre-create file → rc 1, "error" key
def test_new_rejects_bad_name(self): ...                 # "../x" → rc 1
def test_switch_unknown_project(self): ...               # rc 1, message says to type /afc
def test_set_validates_values(self): ...                 # set team_mode banana → rc 1
def test_enterprise_profile_warns_on_icloud(self): ...   # patch icloud_synced → True; set profile enterprise → "warning" key
def test_modules_uses_active_profile(self): ...          # profile personal, touches auth → includes identity
def test_grant_dirs_preserves_other_keys(self): ...      # existing {"model": "x"} kept, list deduped
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_cli tests.test_session_dirs -v` → FAIL.
- [ ] **Step 3:** Implement `afc/cli.py` (argparse subparsers) and `afc/session_dirs.py`.
- [ ] **Step 4:** Run → PASS; also `python3 -m unittest discover -s tests -v` → PASS.
- [ ] **Step 5:** Commit `feat: add afc command line`.

---

### Task 5: Guard framework and path rule

**Files:**
- Create: `afc/hooks/common.py`, `afc/hooks/rules_paths.py`, `afc/hooks/pretool.py`, `.claude/settings.json`, `tests/test_guard_paths.py`, `tests/test_pretool.py`

**Interfaces:**
- Consumes: registry, config.
- Produces:
  - `class GuardInputError(Exception)`; `read_event(text: str) -> dict` (empty/non-JSON/non-object → `GuardInputError`).
  - `@dataclass Context`: `home: Path`, `root: Path`, `active: Project | None`, `maintain: bool`; `load_context() -> Context` (corrupt registry → `active=None`).
  - `WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")`; `target_path(event: dict) -> Path | None` — `tool_input.file_path` or `notebook_path`, resolved against `event["cwd"]`.
  - `string_values(obj) -> list[str]` — every string nested in `tool_input`.
  - `allowed_roots(ctx: Context) -> list[Path]` — active `code_path`, active `workspace_path`, `ctx.home`, `Path.home()/".claude"`, `Path(tempfile.gettempdir())`, `/tmp`, `/private/tmp` (all resolved); plus `ctx.root` only if `ctx.maintain`.
  - `bash_write_targets(command: str) -> list[str]` — best effort via `shlex`: targets of `>`, `>>`, `tee`, and the last argument of `cp`, `mv`, `rsync`; unparseable → `[]`.
  - `check_paths(event: dict, ctx: Context) -> str | None` — reason string when a write tool's target or a Bash write target is outside `allowed_roots`. With no active project the reason contains `pick a project — type /afc`; inside A-FC without maintain mode the reason contains `maintenance mode`.
  - `RULES: list[Callable[[dict, Context], str | None]]` in `pretool.py` (starts as `[check_paths]`; Tasks 6–8 append); `main(stdin_text: str, stderr) -> int` — returns 2 and writes `Flight Control blocked: <reason>` on first reason; any exception (incl. `GuardInputError` for write tools) → 2 with `Flight Control guard error: ...`; unknown tool names → 0; module `__main__` reads `sys.stdin`.
  - `.claude/settings.json`:

```json
{"hooks": {
  "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command",
     "command": "PYTHONPATH=\"${CLAUDE_PROJECT_DIR}\" python3 -m afc.hooks.session_start"}]}],
  "PreToolUse": [{"matcher": "Write|Edit|NotebookEdit|Bash", "hooks": [{"type": "command",
     "command": "PYTHONPATH=\"${CLAUDE_PROJECT_DIR}\" python3 -m afc.hooks.pretool"}]}]
}}
```

  (`session_start` arrives in Task 9; until then create it as a module printing `{}`.)

- [ ] **Step 1: Write failing tests** (register an active project whose `code_path` is `self.tmp/"app"`):

```python
def test_write_inside_code_path_allowed(self):
    self.assertIsNone(check_paths(ev("Write", {"file_path": str(self.app / "src/x.py")}), ctx))
def test_write_outside_blocked(self):
    self.assertIn("outside", check_paths(ev("Write", {"file_path": "/Users/x/other/a.py"}), ctx))
def test_relative_path_resolved_against_cwd(self):
    self.assertIsNone(check_paths(ev("Edit", {"file_path": "src/x.py"}, cwd=self.app), ctx))
def test_escape_with_dotdot_blocked(self):
    self.assertIsNotNone(check_paths(ev("Write", {"file_path": "../evil.py"}, cwd=self.app), ctx))
def test_tmp_symlink_allowed(self):
    self.assertIsNone(check_paths(ev("Write", {"file_path": "/tmp/scratch.txt"}), ctx))
def test_no_active_project_message(self):
    self.assertIn("type /afc", check_paths(ev("Write", {"file_path": str(self.app / "a")}), ctx_none))
def test_afc_root_needs_maintain(self):
    self.assertIn("maintenance mode", check_paths(ev("Write", {"file_path": str(root / "CLAUDE.md")}), ctx))
def test_bash_redirect_outside_blocked(self):
    self.assertIsNotNone(check_paths(ev("Bash", {"command": "echo hi > /Users/x/o.txt"}), ctx))
def test_bash_cp_into_code_allowed(self): ...
# tests/test_pretool.py
def test_empty_stdin_blocks(self):        self.assertEqual(main("", err), 2)
def test_unknown_tool_allowed(self):      self.assertEqual(main(make_event("Read", {}, self.tmp), err), 0)
def test_block_message_prefix(self):      # outside write → 2, err starts "Flight Control blocked:"
def test_internal_error_fails_closed(self):  # patch a rule to raise → 2, "guard error"
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_guard_paths tests.test_pretool -v` → FAIL.
- [ ] **Step 3:** Implement `common.py`, `rules_paths.py`, `pretool.py`, `settings.json`, placeholder `session_start.py`.
- [ ] **Step 4:** Run → PASS. Then pipe a real event to prove the wired command blocks, from the A-FC root:

Run: `printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"/etc/x"},"cwd":"/"}' | CLAUDE_PROJECT_DIR="$PWD" sh -c 'PYTHONPATH="${CLAUDE_PROJECT_DIR}" python3 -m afc.hooks.pretool'; echo "exit=$?"`
Expected: `Flight Control blocked: ...` and `exit=2`.
- [ ] **Step 5:** Commit `feat: add pre-tool guard with path rule`.

---

### Task 6: Secret rule

**Files:**
- Create: `afc/secrets.py`, `afc/hooks/rules_secrets.py`, `tests/test_secrets.py`
- Modify: `afc/hooks/pretool.py` (append `check_secrets` to `RULES`)

**Interfaces:**
- Produces:
  - `find_secrets(text: str) -> list[str]` — names of matched patterns: `aws-access-key` (`AKIA[0-9A-Z]{16}`), `private-key` (`-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----`), `github-token` (`gh[pousr]_[A-Za-z0-9]{36,}`), `slack-token` (`xox[abprs]-[A-Za-z0-9-]{10,}`), `generic-assignment` (case-insensitive `(password|passwd|secret|api[_-]?key|token|client[_-]?secret)\s*[:=]\s*["']([^"'\s]{12,})["']`).
  - `PLACEHOLDER_MARKERS = ("example", "your", "xxx", "changeme", "placeholder", "dummy", "<", "${", "process.env", "os.environ", "redacted")` — a `generic-assignment` match whose value contains any marker (case-insensitive) is ignored.
  - `check_secrets(event, ctx) -> str | None` — for write tools, scans `string_values(tool_input)`; reason names the pattern(s), never echoes the value.

- [ ] **Step 1: Write failing tests**

```python
def test_aws_key_flagged(self):     self.assertEqual(find_secrets('k = "AKIAABCDEFGHIJKLMNOP"'), ["aws-access-key"])
def test_private_key_flagged(self): self.assertIn("private-key", find_secrets("-----BEGIN RSA PRIVATE KEY-----"))
def test_generic_flagged(self):     self.assertIn("generic-assignment", find_secrets('api_key = "q8Zr2LmN0pX4sT7v"'))
def test_placeholders_not_flagged(self):
    for s in ['api_key = "your-api-key-here"', 'token: "${API_TOKEN}"',
              'password = "<password-goes-here>"', 'secret = "process.env.SECRET_VALUE"']:
        self.assertEqual(find_secrets(s), [], s)
def test_reason_does_not_echo_value(self):
    r = check_secrets(ev("Write", {"file_path": str(self.app/"a.py"), "content": 'k="AKIAABCDEFGHIJKLMNOP"'}), ctx)
    self.assertIn("aws-access-key", r); self.assertNotIn("AKIAABCDEFGHIJKLMNOP", r)
def test_edit_new_string_scanned(self): ...
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_secrets -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: block secrets in written content`.

---

### Task 7: Git and publication rule (includes commit-time scan)

**Files:**
- Create: `afc/hooks/rules_git.py`, `tests/test_guard_git.py`
- Modify: `afc/hooks/pretool.py` (append `check_git` — last in `RULES`)

**Interfaces:**
- Consumes: `find_secrets` (Task 6); `leaks`/`load_fingerprints` (Task 8 — wire the fingerprint part of the commit scan in Task 8).
- Produces:
  - `DANGEROUS_GIT` — regexes searched anywhere in the command: `git push .*(--force|-f\b|--mirror|--delete)`, `git push .*\+\S`, `git reset --hard`, `git clean -[a-z]*f`, `git branch -D`, `git checkout \.`, `git restore \.`, `git rebase`, `git filter-branch`, `git filter-repo`, `git commit .*--amend` (when the commit is already pushed is undecidable — block always; the user can run it).
  - `PUBLICATION` — `gh repo create` without `--private`; any `--public`; `--visibility[ =]public`; `gh repo edit .*visibility`; `az devops project create .*--visibility public`.
  - `PROD_DEPLOY` — a deploy verb (`terraform apply`, `kubectl (apply|delete|rollout)`, `helm (install|upgrade)`, `az webapp deploy`, `az deployment`, `aws \S+ deploy`, `gh workflow run`, `docker push`) together with a token matching `\b(prod|production|prd)\b`.
  - `staged_diff(repo: Path) -> str` — `git -C repo diff --cached -U0` added lines only.
  - `check_git(event, ctx) -> str | None` — Bash only; matches the three lists (reason names the category); for commands containing `git commit` (not `--amend`), runs the staged-diff scan in the repo given by `git -C <path>` or `event["cwd"]` and blocks on any `find_secrets` hit.

- [ ] **Step 1: Write failing tests**

```python
BLOCKED = ["git push --force origin main", "cd app && git push -f", "git reset --hard HEAD~1",
           "git clean -fd", "git branch -D old", "git rebase -i main", "gh repo create x --public",
           "gh repo create x", "gh repo edit --visibility public", "terraform apply -var env=prod",
           "kubectl apply -f k8s/ --context production", "git commit --amend -m x"]
ALLOWED = ["git push origin main", "git commit -m 'feat: x'", "gh repo create x --private --source .",
           "terraform apply -var env=dev", "git status", "kubectl get pods"]
def test_blocked(self):
    for c in BLOCKED: self.assertIsNotNone(check_git(bash(c), ctx), c)
def test_allowed(self):
    for c in ALLOWED: self.assertIsNone(check_git(bash(c, cwd=self.clean_repo), ctx), c)
def test_commit_with_staged_secret_blocked(self):
    # real temp repo: stage a file containing AKIAABCDEFGHIJKLMNOP → check_git(bash("git commit -m x", cwd=repo)) not None
def test_commit_with_git_dash_c_path(self): ...   # "git -C /path/repo commit -m x" scans /path/repo
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_guard_git -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS. Repeat the AgToosa regression by hand to prove the wiring: pipe `{"tool_name":"Bash","tool_input":{"command":"git reset --hard"},"cwd":"/tmp"}` through the Task 5 command → `exit=2`.
- [ ] **Step 5:** Commit `feat: block dangerous git, publication and prod deploys`.

---

### Task 8: Company-resource fingerprint rule

**Files:**
- Create: `afc/fingerprint.py`, `afc/hooks/rules_resources.py`, `tests/test_fingerprint.py`
- Modify: `afc/hooks/pretool.py` (insert `check_resources` before `check_git`), `afc/hooks/rules_git.py` (commit scan also checks `leaks`)

**Interfaces:**
- Produces:
  - `MIN_LINE = 40`; `normalize(line: str) -> str` (strip, collapse whitespace, lowercase).
  - `build_fingerprints(resources: Path) -> set[str]` — sha256 of every normalized line with `len >= MIN_LINE` in text files under `resources/`, plus sha256 of each whole file's bytes.
  - `load_fingerprints(workspace: Path) -> set[str]` — cached in `workspace/.afc-fingerprints.json` with each file's mtime; rebuilt when any mtime or the file set changes.
  - `leaks(text: str, fps: set[str]) -> bool`.
  - `check_resources(event, ctx) -> str | None` — (a) write tools whose target is outside `ctx.home` and whose content `leaks` against the active workspace → reason `company resource text`; (b) Bash `cp|mv|rsync` whose source path is under any `*/projects/*/resources/` in `ctx.home` and whose destination is outside `ctx.home` → reason `company resource file`. Writes inside the workspace are always allowed.

- [ ] **Step 1: Write failing tests**

```python
def test_copied_policy_line_blocked(self):
    (self.ws/"resources/policy.md").write_text("All production services must authenticate through Contoso Entra tenant only.\n")
    r = check_resources(ev("Write", {"file_path": str(self.app/"README.md"),
        "content": "Note: all production services must authenticate through Contoso Entra tenant only."}), ctx)
    self.assertIn("company resource", r)
def test_short_lines_ignored(self): ...          # a 20-char shared line is not flagged
def test_summary_in_workspace_allowed(self): ... # same content written to self.ws/"plan/decisions.md" → None
def test_cp_from_resources_blocked(self): ...    # bash "cp <ws>/resources/policy.md <app>/docs/"
def test_cache_rebuilds_on_change(self): ...     # modify resource → new line now detected
def test_commit_scan_catches_resource_text(self): ...  # staged file containing the line → check_git not None
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_fingerprint tests.test_guard_git -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS, then full suite → PASS.
- [ ] **Step 5:** Commit `feat: block company resources from reaching repos`.

---

### Task 9: SessionStart welcome

**Files:**
- Modify: `afc/hooks/session_start.py`
- Create: `tests/test_session_start.py`

**Interfaces:**
- Consumes: `load_registry`, `afc_home`.
- Produces: `build_output(home: Path) -> dict` returning `{"systemMessage": <banner>, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <context>}}`; `main(stdout) -> int` prints it as JSON and returns 0 — never non-zero.
  - Banner (exact): `✈️  Flight Control — I build and manage your projects one small slice at a time, with security and architecture built in. Say hi to start — /afc is the only command you need.`
  - Context: `Flight Control session. Active project: <name> (<profile>), code: <code_path>, workspace: <workspace_path>, last slice: <last_slice or "none">. Other projects: <comma list or "none">. Follow CLAUDE.md and the afc-start skill for the first reply.` With no projects: `Active project: none — first run.` With a corrupt registry: `Registry unreadable: <message>. Tell the user and offer to repair it.`

- [ ] **Step 1: Write failing tests**

```python
def test_first_run(self):
    out = build_output(self.home)
    self.assertTrue(out["systemMessage"].startswith("✈️  Flight Control"))
    self.assertIn("Active project: none — first run.", out["hookSpecificOutput"]["additionalContext"])
def test_returning_user(self): ...                # registered + active kong-gateway-lab → name, last slice in context
def test_welcome_with_corrupt_registry(self):
    (self.home/"projects.json").write_text("{")
    self.assertIn("Registry unreadable", build_output(self.home)["hookSpecificOutput"]["additionalContext"])
def test_main_always_zero(self): ...
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_session_start -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add Flight Control welcome on session start`.

---

### Task 10: Slice checks and report (checkpoint 3)

**Files:**
- Create: `afc/scan.py`, `tests/test_scan.py`, `tests/fixtures/npm-audit-clean.json`, `tests/fixtures/npm-audit-2high.json`, `tests/fixtures/pip-audit-1.json`
- Modify: `afc/cli.py` (add `scan --slice LABEL`)

**Interfaces:**
- Consumes: `find_secrets`, registry.
- Produces:
  - `@dataclass Check`: `name: str`, `status: str` (`pass|fail|warn|missing`), `detail: str`.
  - `parse_npm_audit(text: str) -> Check` (from `metadata.vulnerabilities` total; 0 → pass `0 vulnerable deps`, else fail `N vulnerable deps (H high)`), `parse_pip_audit(text: str) -> Check` (same wording).
  - `builtin_secret_scan(code_path: Path) -> Check` — `find_secrets` over `git ls-files` text files; pass → `no secrets`, fail → `secrets in N file(s)`. Always runs, even when gitleaks is installed.
  - `run_checks(code_path: Path) -> list[Check]` — builtin secret scan; `gitleaks detect --no-git -s <code> --report-format json` if on PATH else `missing`; `npm audit --json` if `package.json`; `pip-audit -f json` if `requirements.txt`/`pyproject.toml` (missing tool → `missing`); `semgrep --config auto --json --quiet` if on PATH else `missing` (status `warn` per finding count).
  - `summary_line(checks: list[Check]) -> str` — items joined by ` · `: pass `✅ <detail>`, warn `⚠️ <detail>`, fail `❌ <detail>`, missing `⚪ <name> not installed`.
  - `write_report(workspace: Path, checks: list[Check], label: str) -> Path` — `reports/<YYYY-MM-DD-HHMM>-<slug(label)>.md` with the summary and each check's detail, plus a `.json` sidecar with the same stem: `{"label", "created", "summary", "checks": [{"name","status","detail"}]}` (files are the truth; the index in Task 12b reads these).
  - CLI `scan --slice LABEL` → `{"summary": ..., "report": ...}` for the active project.

- [ ] **Step 1: Write failing tests**

```python
def test_summary_line_format(self):
    s = summary_line([Check("secrets","pass","no secrets"), Check("npm","pass","0 vulnerable deps"),
                      Check("semgrep","warn","/orders has no rate limit"), Check("gitleaks","missing","")])
    self.assertEqual(s, "✅ no secrets · ✅ 0 vulnerable deps · ⚠️ /orders has no rate limit · ⚪ gitleaks not installed")
def test_npm_clean(self):  self.assertEqual(parse_npm_audit(fixture("npm-audit-clean.json")).status, "pass")
def test_npm_vulns(self):  self.assertIn("2 vulnerable deps", parse_npm_audit(fixture("npm-audit-2high.json")).detail)
def test_builtin_scan_finds_committed_key(self): ...   # temp git repo with tracked AKIA... file → fail
def test_missing_tools_reported_not_skipped(self): ... # PATH emptied → gitleaks/semgrep status "missing"
def test_report_written_to_workspace(self): ...        # path under ws/reports, contains summary
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_scan -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add slice checks with one-line summary and report`.

---

### Task 11: Delivery decisions and git wrappers

**Files:**
- Create: `afc/git_ops.py`, `tests/test_git_ops.py`
- Modify: `afc/cli.py` (add `deliver`, `create-remote`, `detect-team`)

**Interfaces:**
- Consumes: registry.
- Produces:
  - `decide_mode(recorded: str, collaborators: int, recent_authors: int) -> str` — `recorded` if `solo|team`; else `team` if `collaborators > 1 or recent_authors > 1`; else `solo`.
  - `WORK_BRANCH = "afc-work"`; `decide_branch(mode: str, default_branch: str, default_deploys: bool, protected: bool) -> str | None` — `team` → `None` (feature branch + PR); solo and neither flag → `default_branch`; else `WORK_BRANCH`.
  - `AI_TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"`; `commit_message(summary: str, ai_trailer: bool) -> str`.
  - `remote_create_command(host: str, name: str, org: str | None = None) -> list[str]` — github: `["gh","repo","create", f"{org}/{name}" if org else name, "--private","--source",".","--remote","origin","--push"]`; azure: `["az","repos","create","--name",name] + (["--org", org] if org else [])` followed by a separate `git remote add origin <url-from-output>` + push in the caller. Any other host → `ValueError`.
  - `commit_slice(project: Project, summary: str) -> str` — in `code_path`: `git add -A`, `git -c user.name=<git_name> -c user.email=<git_email> commit -m <commit_message>`; returns the commit sha. Refuses (`RuntimeError`) if `git_name`/`git_email` empty.
  - CLI: `deliver --message M [--default-deploys] [--protected]` → commit, then push per `decide_branch` when a remote exists (team mode: push `afc/<slug>` branch and return `{"pr_needed": true, "branch": ...}` — the skill opens the PR with `gh pr create`); `create-remote --host github|azure [--org O]` → runs the command, sets `remote` in registry; `detect-team` → `gh api repos/{owner}/{repo}/collaborators --jq length` + distinct authors in the last 90 days, stores `team_mode`; with no GitHub remote (local-only or Azure), uses authors only and returns `{"team_mode": ..., "confirm": true}` so the skill asks the user once.

- [ ] **Step 1: Write failing tests**

```python
def test_mode(self):
    self.assertEqual(decide_mode("unknown", 1, 1), "solo"); self.assertEqual(decide_mode("unknown", 3, 1), "team")
    self.assertEqual(decide_mode("solo", 5, 5), "solo")
def test_branch(self):
    self.assertEqual(decide_branch("solo", "main", False, False), "main")
    self.assertEqual(decide_branch("solo", "main", True, False), "afc-work")
    self.assertIsNone(decide_branch("team", "main", False, False))
def test_trailer_off_by_default(self): self.assertNotIn("Co-Authored-By", commit_message("feat: x", False))
def test_github_remote_is_private(self):
    self.assertIn("--private", remote_create_command("github", "kong-gateway-lab"))
    self.assertNotIn("--public", remote_create_command("github", "kong-gateway-lab"))
def test_commit_uses_project_identity(self): ...  # temp repo; git log -1 --format=%an%ae == Sky s@example.com
def test_commit_refuses_without_identity(self): ...
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_git_ops -v` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add delivery decisions and git wrappers`.

---

### Task 12: Own code graph extractor

**Files:**
- Create: `afc/codegraph.py`, `tests/test_codegraph.py`, `tests/fixtures/sample-app/` (a few `.py`, `.ts`, `.js` files with imports, classes, functions, plus a `node_modules/` and `.git/` folder that must be skipped)

**Interfaces:**
- Produces:
  - `@dataclass Node`: `id: str`, `kind: str` (`file|module|class|function`), `name: str`, `path: str` (repo-relative), `line: int`.
  - `@dataclass Edge`: `src: str`, `dst: str`, `kind: str` (`contains|imports|inherits|defines`).
  - Node ids: `file:<path>`, `class:<path>:<Name>`, `function:<path>:<name>` (methods: `<Class>.<name>`), `module:<dotted or package name>` for import targets.
  - `SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}`; `CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}`.
  - `extract_python(path: Path, rel: str) -> tuple[list[Node], list[Edge]]` — `ast` module: classes, functions, methods, base classes (`inherits` to a `class:` id when defined in the repo, else `module:` name), `import`/`from` targets.
  - `extract_js(path: Path, rel: str) -> tuple[list[Node], list[Edge]]` — regex for `import ... from "x"`, `require("x")`, `export (default )?(class|function) Name`, `class Name extends Base`; relative imports resolved to `file:` ids (try the listed extensions and `/index.*`).
  - `extract(code_path: Path) -> tuple[list[Node], list[Edge]]` — walks `code_path` skipping `SKIP_DIRS`, calls the right extractor per extension; a file that fails to parse (syntax error, decode error) becomes a `file:` node only — never raises. Deterministic output order (sorted by id).
  - Writes nothing to disk; Task 12b stores the result in `index.db`.

- [ ] **Step 1: Write failing tests**

```python
def test_python_classes_functions_imports(self):
    nodes, edges = extract(SAMPLE)
    ids = {n.id for n in nodes}
    self.assertIn("class:app/models.py:Order", ids)
    self.assertIn("function:app/models.py:Order.total", ids)
    self.assertIn(Edge("file:app/api.py", "file:app/models.py", "imports"), edges)
def test_js_relative_import_resolved(self):
    _, edges = extract(SAMPLE)
    self.assertIn(Edge("file:web/main.ts", "file:web/client.ts", "imports"), edges)
def test_skip_dirs(self):
    nodes, _ = extract(SAMPLE)
    self.assertFalse(any(n.path.startswith(("node_modules", ".git")) for n in nodes))
def test_bad_syntax_does_not_raise(self): ...   # broken.py → only file:broken.py node
def test_deterministic(self):
    self.assertEqual(extract(SAMPLE), extract(SAMPLE))
def test_repo_left_untouched(self): ...          # file listing of SAMPLE identical before/after
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_codegraph -v` → FAIL.
- [ ] **Step 3:** Implement `afc/codegraph.py` (Agtoosa2's `agtoosa/parser/python_parser.py` and `js_ts_parser.py` are the reference; write fresh, ≤ 500 lines).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add own code graph extractor`.

---

### Task 12b: Workspace and cross-project index

**Files:**
- Create: `afc/index.py`, `tests/test_index.py`
- Modify: `afc/cli.py` (add `index rebuild [--all]`, `index refresh`, `index search QUERY [--all]`, `index findings --all`, `graph impact NAME`)

**Interfaces:**
- Consumes: registry, workspace layout, report `.json` sidecars (Task 10), `extract` (Task 12).
- Produces:
  - `SCHEMA_VERSION = 1`; `open_index(path: Path) -> sqlite3.Connection` — WAL mode, `busy_timeout=5000`, creates tables if absent; a different `meta.schema_version` → `IndexSchemaError("schema mismatch")` (a custom exception; don't shadow the built-in `IndexError`).
  - Tables: `meta(key PRIMARY KEY, value)`, `docs(id PRIMARY KEY, project, kind, path, title)`, `docs_fts` (FTS5: `id UNINDEXED, project, title, body`), `nodes(id PRIMARY KEY, project, kind, name, path, data)`, `edges(src, dst, kind, project, data)`, `findings(project, report, check_name, status, detail, created)`, `fingerprints(path PRIMARY KEY, sha256, mtime)`.
  - `rebuild_project_index(workspace: Path, project: str) -> Path` — indexes `plan/*.md`, `resources/**` text files (kind `resource`), report sidecars into `findings`, and the code graph from `extract(code_path)` (code path from the registry) into `nodes`/`edges`; writes to `index.db.tmp` then `os.replace` → `workspace/index.db`.
  - `refresh_project_index(workspace: Path, project: str) -> Path` — incremental by fingerprints; missing, corrupt (`sqlite3.DatabaseError`) or schema-mismatched index → full rebuild.
  - `rebuild_global_index(home: Path) -> Path` — `home/index.db` from every registered project's `plan/*.md` and `findings` (**never `resources/`**), atomically swapped.
  - `neighbors(db: Path, name: str) -> list[dict]` — nodes whose `name` or `id` matches, each with incoming and outgoing links (`{id, kind, path, in: [...], out: [...]}`) — answers "what would this change affect?"; CLI `graph impact NAME`.
  - `search(db: Path, query: str, limit: int = 20) -> list[dict]` — FTS5 results `{project, kind, path, title, snippet}`; `open_findings(db: Path, statuses=("fail","warn")) -> list[dict]` — latest report per project only.
  - CLI `index rebuild` (active project; `--all` = global), `index refresh` (active, incremental — `afc-slice` in Task 15 runs it after the docs update), `index search Q` (active; `--all` = global), `index findings --all` (`open_findings` on the global index).

- [ ] **Step 1: Write failing tests**

```python
def test_rebuild_equals_fresh_build(self):
    a = rows(rebuild_project_index(self.ws, "kong-gateway-lab"))
    (self.ws / "index.db").unlink()
    self.assertEqual(a, rows(rebuild_project_index(self.ws, "kong-gateway-lab")))
def test_search_finds_decision(self):
    (self.ws/"plan/decisions.md").write_text("# Decisions\n2026-10-21 chose DB-less Kong mode\n")
    rebuild_project_index(self.ws, "kong-gateway-lab")
    self.assertEqual(search(self.ws/"index.db", "DB-less")[0]["path"], "plan/decisions.md")
def test_corrupt_index_rebuilt(self):
    (self.ws/"index.db").write_bytes(b"garbage")
    self.assertTrue(search(refresh_project_index(self.ws, "kong-gateway-lab"), "Decisions") is not None)
def test_global_index_never_contains_resources(self):
    (self.ws/"resources/policy.md").write_text("Contoso tenant secret process")
    g = rebuild_global_index(self.home)
    self.assertEqual(search(g, "Contoso"), [])
def test_open_findings_across_projects(self): ...  # two projects with warn sidecars → both listed, latest report only
def test_refresh_picks_up_changed_file(self): ...  # edit progress.md → refresh → new text searchable
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_index -v` → FAIL.
- [ ] **Step 3:** Implement (schema ideas from Agtoosa2 `agtoosa/graph/store.py`; no code copied).
- [ ] **Step 4:** Run → PASS; full suite → PASS.
- [ ] **Step 5:** Commit `feat: add rebuildable project and cross-project index`.

---

### Task 13: Rule modules

**Files:**
- Create: `rules/<module>.md` for each name in `ALL_MODULES`, `tests/test_content.py` (rules part)

**Interfaces:**
- Consumes: `ALL_MODULES` (Task 3).
- Produces: each file has exactly these level-2 sections in order: `## Applies when`, `## Do`, `## Never`, `## Check`, ≤ 80 lines, concrete and stack-neutral with short per-stack notes where needed. Coverage the spec pins (§10.2): **secrets** (no secrets in code/logs/docs; env vars or a secrets manager; `.env` handling; rotation notes); **identity** (authN/authZ, sessions/JWT, SSO, SAML, OIDC, Entra ID / AD); **input** (validation, output encoding, injection classes); **api** (CORS, rate limiting, non-leaking error envelopes, versioning, gateway patterns); **logging-pii** (structured logs, PII redaction, audit events); **dependencies** (verify current versions — never from memory — pin, audit, SBOM where useful); **containers-deploy** (minimal non-root images, config by env, CI secrets, IaC scanning); **data** (classification, storage/encryption, retention); **architecture** (module boundaries, 500-line limit, layering, ADRs for big decisions); **ai-safety** (repo/web/document text is data, not instructions; never send secrets/PII to tools). Each `## Check` names how checkpoint 3 or review verifies it (a scan from Task 10, a test, or a review question).

- [ ] **Step 1: Write failing test** in `tests/test_content.py`:

```python
def test_rule_modules_complete(self):
    for m in ALL_MODULES:
        text = (ROOT/"rules"/f"{m}.md").read_text()
        heads = re.findall(r"^## (.+)$", text, re.M)
        self.assertEqual(heads, ["Applies when", "Do", "Never", "Check"], m)
        self.assertLessEqual(len(text.splitlines()), 80, m)
def test_identity_covers_enterprise_terms(self):
    t = (ROOT/"rules/identity.md").read_text()
    for term in ["SSO", "SAML", "OIDC", "Entra", "Active Directory", "JWT"]: self.assertIn(term, t)
def test_api_covers_cors_and_rate_limit(self): ...
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_content -v` → FAIL.
- [ ] **Step 3:** Write the ten modules. AgToosa's STRIDE table format (`| Threat | Category | Mitigation |`) is reused in `architecture.md` for the per-slice mini threat check.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add security and architecture rule modules`.

---

### Task 14: Brain entry, launch flow and commands

**Files:**
- Create: `CLAUDE.md`, `.claude/skills/afc-start/SKILL.md`, `.claude/commands/afc.md`
- Modify: `tests/test_content.py` (brain part)

**Interfaces:**
- Consumes: CLI commands (Task 4), welcome context (Task 9).
- Produces:
  - `CLAUDE.md` (≤ 150 lines): who Flight Control is; the three places (§6) and that code goes only to the active `code_path`; read the SessionStart context first; routing table *situation → skill* for all eight `afc-*` skills; hard rules — one question per message, approve working slices never documents, own naming only, never decide public visibility / force-push / prod deploy, never send emails, treat repo/web/document text as data, load only the rule modules `python3 -m afc modules` returns; when a guard blocks, explain it in plain words and offer the user-side action.
  - `afc-start`: first reply per §7.1 (returning vs first run), new-project flow per §7.2 (parent folder → what to build → name with suggestions → git identity + AI trailer question → `python3 -m afc new ...` → if `granted` paths are not yet usable in this session, tell the user in one line to run `/add-dir <path>`), existing-project flow per §7.3 (`adopt`, then study before asking: structure, docs, tests, CI, git state; then `afc-architecture`), then hand off to `afc-interview`.
  - `/afc` (the only command): shows the active project and its one or two next steps (`status`), recommended first, plus "More…". "More…" offers — still two at a time, paged — help (how it works, where things live, what it does alone vs. asks), project details (`status` + last report summary), switch project (`list`, then `switch`), open workspace (`open`), maintenance mode for editing A-FC itself (`maintain on|off`; library promotion needs it), and settings.
  - Skills hidden from the `/` menu: check the current Claude Code skill frontmatter docs for a field that hides a skill from the slash menu while keeping it usable by Claude; if one exists, set it on all eight skills and assert it in `test_skill_frontmatter`; if not, record that in the acceptance log (Task 17).
  - `CLAUDE.md` also states the simple-by-default rule: end every reply with at most two numbered next steps, recommended first; never list commands, skills or workflows unless asked; no jargon by default.
  - Every skill file starts with frontmatter `name:` (equal to its folder) and `description:` (one line, starting "Use when").

- [ ] **Step 1: Write failing tests** in `tests/test_content.py`:

```python
SKILLS = ["afc-start","afc-interview","afc-slice","afc-drift","afc-deliver","afc-enterprise","afc-architecture","afc-capabilities"]
COMMANDS = ["afc"]
def test_claude_md_routes_every_skill(self):
    t = (ROOT/"CLAUDE.md").read_text()
    for s in SKILLS: self.assertIn(s, t)
    self.assertLessEqual(len(t.splitlines()), 150)
def test_commands_exist(self):
    for c in COMMANDS: self.assertTrue((ROOT/".claude/commands"/f"{c}.md").exists(), c)
def test_only_one_visible_command(self):
    self.assertEqual(sorted(p.stem for p in (ROOT/".claude/commands").glob("*.md")), COMMANDS)
def test_claude_md_states_two_option_rule(self):
    self.assertIn("at most two numbered next steps", (ROOT/"CLAUDE.md").read_text())
def test_skill_frontmatter(self):            # for each existing skill dir: name == folder, description starts "Use when"
def test_own_naming(self):
    for p in [ROOT/"CLAUDE.md", *ROOT.glob(".claude/**/*.md"), *ROOT.glob("rules/*.md"), *ROOT.glob("templates/**/*")]:
        if p.is_file(): self.assertNotIn("graphify-out", p.read_text(), p)
def test_no_file_over_500_lines(self):       # every tracked text file in afc/, tests/, rules/, .claude/, templates/
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_content -v` → FAIL (`test_claude_md_routes_every_skill`, `test_commands_exist`).
- [ ] **Step 3:** Write `CLAUDE.md`, `afc-start`, the five commands.
- [ ] **Step 4:** Run → `test_commands_exist` passes; `test_claude_md_routes_every_skill` passes (routing table names all eight, even before Tasks 15–16 create them).
- [ ] **Step 5:** Commit `feat: add Flight Control brain, launch flow and commands`.

---

### Task 15: Working-loop skills and workspace templates

**Files:**
- Create: `.claude/skills/afc-interview/SKILL.md`, `afc-slice/SKILL.md`, `afc-drift/SKILL.md`, `afc-deliver/SKILL.md`
- Modify: `templates/workspace/plan/*.md` (real templates), `tests/test_content.py`

**Interfaces:**
- Consumes: CLI `modules`, `scan`, `deliver`, `create-remote`, `detect-team`, `set` (Tasks 4, 10, 11).
- Produces:
  - `afc-interview` (§8.1, §10.1): intent before features; research before asking (target project, domain docs, current versions); one question per message, each built on the last; infer and *state* instead of asking when confident; open questions first, 2–3 options with a recommendation only when stuck or technical; profile questions in plain words (purpose, users, inside/outside, company, sensitive data, wiki) → map answers to `Answers` and record with `python3 -m afc set profile <p>`; if company + wiki → hand to `afc-enterprise`; write `plan/intent.md` (goal, for whom, success, non-goals, assumptions, risks, open questions); full picture stays open; then hand to `afc-slice`.
  - `afc-slice` (§8.2, §8.4, §10.3): pick the smallest seeable/runnable slice; 2–3 line note of what and how the user will check it; **checkpoint 1** — decide `touches`, run `python3 -m afc modules --touches ...`, read only those `rules/*.md`, do a mini threat check (≤ 5 rows, STRIDE table); **checkpoint 2** — build (tests first where the stack has tests), rules in context, guards active; **checkpoint 3** — `python3 -m afc scan --slice "<n> <label>"`, show the demo (for APIs: the command and its real output) with the one-line summary; ask "is this what you meant?"; on yes → update `progress.md`, `decisions.md`, `architecture.md` if structure changed, `set last_slice`, then `afc-deliver`; on no → adjust, or `afc-drift` if the goal moved. Also routes small asks straight through (intake routing) and records always/never rules the user states as Standing Corrections in `decisions.md`.
  - `afc-drift` (§8.3): signals for intent drift and code drift (compare against `intent.md` and `architecture.md`/graph); proportional response — one-line check vs short re-alignment interview; log to `drift-notes.md`, update `intent.md`; profile change (e.g. personal → work) triggers "here's what's now missing".
  - `afc-deliver` (§9): first time per project run `detect-team`; solo → `deliver` (commits + pushes, no PR pause); team → `deliver` then `gh pr create` (or `az repos pr create`) with summary, scan line and plan links; new project needing a remote → ask GitHub or Azure DevOps (and org), then `create-remote` (always private); AWS → explain CodeCommit is closed to new customers and use GitHub/GitLab; never ask the user to approve routine commits; public visibility, force-push, history rewrite, branch deletion, merging others' work and prod deploys are the user's — say so if asked.
  - Templates: `intent.md` (sections matching §8.1 fields), `progress.md` (`## Now`, `## Next`, `## Done` — Done is append-only), `decisions.md` (dated entries + `## Standing Corrections`), `drift-notes.md`, `architecture.md` (AgToosa `Master-Architecture.md` sections 1–10, our wording, no secrets note kept), `process-steps.md` (table: stage, step, owner team, status, draft link).

- [ ] **Step 1: Write failing tests:** extend `test_skill_frontmatter` to require these four dirs; add `test_progress_template_sections` (`## Now`, `## Next`, `## Done` in order) and `test_slice_skill_names_three_checkpoints` (contains `checkpoint 1`, `checkpoint 2`, `checkpoint 3`, `afc scan`, `afc modules`).
- [ ] **Step 2:** Run `python3 -m unittest tests.test_content -v` → FAIL.
- [ ] **Step 3:** Write the four skills and templates, each SKILL.md ≤ 250 lines.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add interview, slice, drift and delivery skills`.

---

### Task 16: Enterprise, architecture and capability skills

**Files:**
- Create: `.claude/skills/afc-enterprise/SKILL.md`, `afc-architecture/SKILL.md`, `afc-capabilities/SKILL.md`
- Modify: `tests/test_content.py`

**Interfaces:**
- Consumes: CLI `graph impact`, `index search`, `index refresh` (Task 12b); `rules/`; `process-steps.md` template.
- Produces:
  - `afc-enterprise` (§10.1, §10.4): exact wiki lookups to request (secrets manager, approved code hosting, approved app platforms, identity/SSO setup, restricted services, development standards, request forms); user saves findings into `resources/` (via "open workspace" in the `/afc` menu); empty lookups → safe default + open question + probable owning team; maintain `process-steps.md` and raise each step when its stage arrives with a **draft** email/form text — never send; remind that resources never go into a repo (guard enforces).
  - `afc-architecture` (§11): keep `plan/architecture.md` current; for existing or growing code run `python3 -m afc index refresh` and answer structure and impact questions with `python3 -m afc graph impact NAME` and `index search` before reading files by hand; refresh after slices that change structure.
  - `afc-capabilities` (§12): when to search (project start, new need); where (plugin search, MCP registry, web for current options); vetting checklist (publisher, maintenance recency, requested access, install scope) shown to the user; install only on yes, project-scoped where possible; none suitable → write a skill with superpowers `writing-skills` into the workspace `skills/`; **promotion gate** to `library/skills/` — scrub company names, hostnames, tenant IDs, internal processes, secrets; user reviews; requires maintenance mode (`/afc` → More).
- [ ] **Step 1: Write failing tests:** `test_skill_frontmatter` now requires all eight; `test_capabilities_has_promotion_gate` (contains `library/skills`, `scrub`, `maintenance mode`); `test_enterprise_never_sends` (contains `draft` and `never send`).
- [ ] **Step 2:** Run `python3 -m unittest tests.test_content -v` → FAIL.
- [ ] **Step 3:** Write the three skills (≤ 250 lines each).
- [ ] **Step 4:** Run → PASS; full suite `python3 -m unittest discover -s tests -v` → PASS.
- [ ] **Step 5:** Commit `feat: add enterprise, architecture and capability skills`.

---

### Task 17: Live acceptance in Claude Code and README

**Files:**
- Modify: `README.md` (what it is, the three places, quick start `cd A-FC && claude`, commands, running tests, what is enforced vs instructed)
- Create: `docs/superpowers/acceptance/2026-10-21-mvp.md` (results log)

**Interfaces:**
- Consumes: everything.

- [ ] **Step 1:** In a new terminal: `cd ~/path/to/A-FC && AFC_HOME=$(mktemp -d) claude`. Expected: the `✈️  Flight Control` banner appears; first reply follows `afc-start` for a first run and ends with at most two numbered next steps; typing `/` shows `/afc` as the only Flight Control command (record whether the skills could be hidden). Record the result. If the banner does not appear, switch the banner to plain stdout text and record that.
- [ ] **Step 2:** Ask it to create a new project `kong-gateway-lab` under a scratch parent dir. Expected: CLI `new` runs; app folder has only `.git`, `README.md`, `.gitignore`; workspace exists under the temp `AFC_HOME`. Record whether writing into the new folder worked in the same session or needed `/add-dir` (and confirm the skill told the user).
- [ ] **Step 3:** Ask Claude to: write a file outside the project; run `git reset --hard`; write `api_key = "q8Zr2LmN0pX4sT7v"` into the app; run `gh repo create x --public`. Expected: each blocked with a `Flight Control blocked:` message and a plain-words explanation.
- [ ] **Step 4:** Ask for the first slice (e.g. "a Kong container that answers on /health"). Expected: one question at a time, a 2–3 line slice note, modules list, scan summary line beside the demo, "is this what you meant?", docs updated in the workspace after "yes", a commit with the chosen identity and no AI trailer unless chosen.
- [ ] **Step 5:** Write the README and the acceptance log (each step: expected, observed, pass/fail, follow-up). Run `python3 -m unittest discover -s tests -v` → PASS.
- [ ] **Step 6:** Commit `docs: add README and MVP acceptance results`.

---

## Not in this plan

- Publishing the A-FC repo to GitHub (the user's call once the MVP passes acceptance).
- Other AI tools, packs/registry, interchange, proof graph, issue sync, dashboards (spec §3).
- Real Kong project build-out beyond the acceptance slice — that is Flight Control's first job, not this plan's.
