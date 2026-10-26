"""slice record: tick a finished slice, log the decision and note the architecture in one call.

Writes where the skills used to tell the session to write: the spec in plan/specs/,
plan/decisions.md and plan/architecture.md. Nothing is written unless all three can be.
"""

import argparse
import re

from afc import cli_plan, plan
from afc.cli_plan import _cli, _error, _find, _load, _read_spec

NAMES = ("slice",)
LINKS = "## 9. Decision links"


def register(sub) -> None:
    p = sub.add_parser("slice", help="record a finished slice")
    p.set_defaults(handler=cmd_record)  # bare `slice` reports the missing subcommand
    ssub = p.add_subparsers(dest="slice_command")
    q = ssub.add_parser("record", help="tick the slice, log the decision, note the architecture")
    q.add_argument("id")
    q.add_argument("slice", type=int)
    q.add_argument("--decision", required=True)
    q.add_argument("--architecture", required=True)
    q.set_defaults(handler=cmd_record)


def _tick(spec_text: str, n: int) -> str | None:
    """The spec with slice n ticked, or None when it has no such slice."""
    lines = spec_text.split("\n")
    try:
        start, end = plan._section_span(lines, "Slices")
    except ValueError:
        return None
    for i in range(start, end):
        m = re.match(r"(\s*- \[)[ xX](\]\s*)(\d+)\.", lines[i])
        if m and int(m.group(3)) == n:
            lines[i] = m.group(1) + "x" + lines[i][m.start(2):]
            return "\n".join(lines)
    return None


def _append_architecture(text: str, entry: str) -> str:
    """Add a bullet at the end of section 9 (Decision links), or at the end of the file."""
    lines = text.rstrip("\n").split("\n")
    for i, line in enumerate(lines):
        if line.strip() == LINKS:
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                j += 1
            while j > i + 1 and not lines[j - 1].strip():
                j -= 1
            lines.insert(j, entry)
            return "\n".join(lines) + "\n"
    return "\n".join(lines) + "\n\n" + entry + "\n"


def cmd_record(args: argparse.Namespace) -> dict:
    if not getattr(args, "slice_command", None):
        raise _error("Use `slice record <spec-id> <slice-number> --decision TEXT --architecture TEXT`.")
    space, _, text = _load()
    sid, n = args.id, args.slice
    decision, arch = " ".join(args.decision.split()), " ".join(args.architecture.split())
    if not decision or not arch:
        raise _error("Give both a decision and an architecture note.")
    section, row = _find(space, text, sid)
    started = False
    if section == "Next":
        try:
            cli_plan.cmd_start(argparse.Namespace(id=sid))
            started = True
        except Exception:
            pass  # another spec is in progress; recording still works
        space, _, text = _load()
        _, row = _find(space, text, sid)
    spec_path, spec_text = _read_spec(space, sid, row)
    ticked = _tick(spec_text, n)
    if ticked is None:
        raise _error(f"{sid} has no slice {n}.")
    decisions, architecture = space.base / "decisions.md", space.base / "architecture.md"
    for path in (decisions, architecture):
        if not path.is_file():
            raise _error(f"This project has no {path.name}. A health check repair adds it.")
    dec_text = decisions.read_text(encoding="utf-8")
    arch_text = architecture.read_text(encoding="utf-8")
    today = _cli()._today()
    entry = f"### {today} — {sid} slice {n}\n{decision}\n"
    new_dec = dec_text.rstrip("\n") + "\n\n" + entry
    new_arch = _append_architecture(arch_text, f"- {today} {sid} slice {n}: {arch}")
    old = {spec_path: spec_text, decisions: dec_text, architecture: arch_text}
    new = {spec_path: ticked, decisions: new_dec, architecture: new_arch}
    try:
        for path, content in new.items():
            path.write_text(content, encoding="utf-8")
    except BaseException:
        for path, content in old.items():
            path.write_text(content, encoding="utf-8")
        raise
    open_ = plan.open_slices(ticked)
    out = {"recorded": sid, "slice": n, "open_slices": open_}
    if started:
        out["plan_started"] = True
    if not open_:
        try:
            out["plan_done"] = cli_plan.cmd_done(argparse.Namespace(id=sid))["done"]
        except Exception as exc:  # not ready yet: the ship check says what is missing
            out["plan_open"] = str(exc)
    return out
