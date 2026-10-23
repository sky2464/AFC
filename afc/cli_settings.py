"""Values `afc set` accepts for each project field, checked before they are saved."""

from afc.profile import PROFILES

TEAM_MODES = ("solo", "team", "unknown")
REMOTES = ("none", "github", "azure")


class SettingError(ValueError):
    """A setting value was rejected; the message is shown to the user."""


def _one_of(allowed: tuple[str, ...]):
    def check(field: str, raw: str) -> str:
        if raw not in allowed:
            raise SettingError(f"{field} must be one of: {', '.join(allowed)}.")
        return raw

    return check


def _true_or_false(field: str, raw: str) -> bool:
    if raw not in ("true", "false"):
        raise SettingError(f"{field} must be true or false.")
    return raw == "true"


def _free_text(field: str, raw: str) -> str:
    return raw


SETTABLE = {
    "profile": _one_of(PROFILES),
    "team_mode": _one_of(TEAM_MODES),
    "remote": _one_of(REMOTES),
    "ai_trailer": _true_or_false,
    "last_slice": _free_text,
    "git_name": _free_text,
    "git_email": _free_text,
}
