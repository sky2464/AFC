"""Project registry: which projects exist and which one is active.

projects.json (under the workspace root) is the machine source of truth.
projects.md next to it is a human-readable view, regenerated on every save.
"""

import dataclasses
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class RegistryError(Exception):
    """A registry rule was broken: bad name, duplicate, unknown project, unreadable file."""


@dataclass
class Project:
    name: str
    code_path: str
    workspace_path: str
    profile: str = "unknown"
    status: str = "active"
    last_active: str = ""
    last_slice: str = ""
    git_name: str = ""
    git_email: str = ""
    ai_trailer: bool = False
    team_mode: str = "unknown"  # solo | team | unknown
    remote: str = "none"  # none | github | azure


@dataclass
class Registry:
    projects: dict[str, Project] = field(default_factory=dict)
    active_name: str | None = None

    def add(self, p: Project) -> None:
        validate_name(p.name)
        if p.name in self.projects:
            raise RegistryError(f"project already exists: {p.name}")
        self.projects[p.name] = p

    def get(self, name: str) -> Project | None:
        return self.projects.get(name)

    def set_active(self, name: str) -> None:
        if name not in self.projects:
            raise RegistryError(f"unknown project: {name}")
        self.active_name = name

    def remove(self, name: str) -> Project:
        project = self.projects.pop(name, None)
        if project is None:
            raise RegistryError(f"unknown project: {name}")
        if self.active_name == name:
            self.active_name = None
        return project

    def active(self) -> Project | None:
        if self.active_name is None:
            return None
        return self.projects.get(self.active_name)

    def update(self, name: str, /, **fields: object) -> Project:
        project = self.projects.get(name)
        if project is None:
            raise RegistryError(f"unknown project: {name}")
        allowed = {f.name for f in dataclasses.fields(Project)} - {"name"}
        unknown = sorted(set(fields) - allowed)
        if unknown:
            raise RegistryError(f"unknown project field(s): {', '.join(unknown)}")
        for key, value in fields.items():
            setattr(project, key, value)
        return project


def validate_name(name: str) -> str:
    """Return the name if it is a legal project name, else raise RegistryError."""
    if not NAME_RE.fullmatch(name):
        raise RegistryError(
            f"invalid project name {name!r}: use 2-63 lowercase letters, digits or hyphens, "
            "starting with a letter or digit"
        )
    return name


def load_registry(home: Path) -> Registry:
    """Read home/projects.json. A missing file means an empty registry.

    Bad or duplicate names raise RegistryError; an `active` that names no project loads as None.
    """
    path = home / "projects.json"
    if not path.exists():
        return Registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [Project(**entry) for entry in data.get("projects", [])]
        active = data.get("active")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RegistryError(f"projects.json is unreadable: {exc}") from exc
    projects: dict[str, Project] = {}
    for project in entries:
        if not isinstance(project.name, str):
            raise RegistryError("projects.json is unreadable: a project name is not text")
        validate_name(project.name)
        if project.name in projects:
            raise RegistryError(f"projects.json is unreadable: duplicate project {project.name}")
        projects[project.name] = project
    if active is not None and not isinstance(active, str):
        raise RegistryError("projects.json is unreadable: 'active' must be a string or null")
    if active not in projects:
        active = None
    return Registry(projects=projects, active_name=active)


def save_registry(home: Path, reg: Registry) -> None:
    """Write projects.md, then projects.json (the source of truth), each atomically.

    If the view can't be written, the registry is left as it was.
    """
    home.mkdir(parents=True, exist_ok=True)
    data = {
        "active": reg.active_name,
        "projects": [dataclasses.asdict(p) for p in reg.projects.values()],
    }
    _atomic_write(home / "projects.md", _render_markdown(reg))
    _atomic_write(home / "projects.json", json.dumps(data, indent=2) + "\n")


def _render_markdown(reg: Registry) -> str:
    lines = [
        "# Flight Control projects",
        "",
        f"Active: {reg.active().name if reg.active() else 'none'}",
        "",
        "| Name | Profile | Status | Last active | Code path |",
        "|---|---|---|---|---|",
    ]
    for p in reg.projects.values():
        lines.append(
            f"| {p.name} | {p.profile} | {p.status} | {p.last_active or '-'} | {p.code_path} |"
        )
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
