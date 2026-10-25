"""The readiness gate for finishing a spec (FC-015).

gate() lists, in plain words, what is still missing before a spec can be called finished. It
only reads: it runs the project's own test command and looks at git, and changes nothing.
The project's test command is the line `Test command: <command>` in plan/architecture.md of its
workspace; with none recorded the gate counts the tests as missing, never as passing. Flight
Control's own plan uses its known suite command.
"""

import re
import shlex
import subprocess
from pathlib import Path

from afc import plan

FC_TEST_COMMAND = "python3 -m unittest discover -s tests"
TEST_TIMEOUT = 600
NO_TEST_COMMAND = ("No test command is recorded for this project, so the tests were never run. "
                   "Record it as a line `Test command: <command>` in plan/architecture.md.")


def recorded_test_command(workspace: Path) -> str | None:
    path = Path(workspace) / "plan" / "architecture.md"
    if not path.is_file():
        return None
    m = re.search(r"^Test command:[ \t]*`?([^`\n]+?)`?[ \t]*$", path.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def open_slices(spec_text: str) -> list[str]:
    open_ = plan.open_slices(spec_text)
    if not open_ and not plan.all_slices(spec_text):
        return ["The spec has no slices yet."]
    return [f"A slice is not ticked: {s}" for s in open_]


def tests_green(code: Path, command: str | None) -> list[str]:
    if not command:
        return [NO_TEST_COMMAND]
    try:
        done = subprocess.run(shlex.split(command), cwd=code, capture_output=True, text=True,
                              timeout=TEST_TIMEOUT)
    except FileNotFoundError:
        return [f"The test command could not be started: {command}"]
    except subprocess.TimeoutExpired:
        return [f"The test suite did not finish within {TEST_TIMEOUT} seconds."]
    if done.returncode != 0:
        return [f"The test suite is failing (`{command}`)."]
    return []


def clean_tree(code: Path) -> list[str]:
    done = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=code, capture_output=True,
                          text=True)
    if done.returncode != 0:
        return ["The code folder is not a readable git repository."]
    changed = [l for l in done.stdout.splitlines() if l.strip()]
    if changed:
        return [f"There are uncommitted changes in the code folder ({len(changed)} file(s))."]
    return []


def gate(spec_text: str, code: Path, test_command: str | None) -> dict:
    """What is missing before the spec is finished; ready only when nothing is."""
    missing = [*open_slices(spec_text), *tests_green(code, test_command), *clean_tree(code)]
    return {"ready": not missing, "missing": missing,
            "next": "Ready to finish." if not missing else missing[0]}


CHANGELOG_HEAD = "# Changelog\n"


def changelog_entry(spec_text: str, sid: str, title: str, today: str) -> str:
    """One entry in the user's words: the date, the spec's goal and the slices that shipped.

    Written from the Goal section and the slice labels, never from commit subjects."""
    lines = spec_text.split("\n")
    goal = ""
    try:
        start, end = plan._section_span(lines, "Goal")
        paragraph: list[str] = []
        for line in lines[start:end]:
            if line.strip():
                paragraph.append(line.strip())
            elif paragraph:
                break
        goal = " ".join(paragraph)
    except ValueError:
        pass
    out = [f"## {today} — {sid} {title}", ""]
    if goal:
        out += [goal, ""]
    for _, label in plan.all_slices(spec_text):
        label = re.sub(r"^\d+\.\s*", "", label)
        label = re.split(r"\s+—\s+you'll check", label)[0].strip()
        out.append(f"- {label}")
    return "\n".join(out) + "\n"


def add_to_changelog(current: str, entry: str) -> str:
    """Put the entry first, under the heading; one entry per spec, newest on top."""
    body = current if current.strip() else CHANGELOG_HEAD
    head, _, rest = body.partition("\n## ")
    head = head.rstrip("\n") + "\n"
    return head + "\n" + entry + (("\n## " + rest) if rest else "")
