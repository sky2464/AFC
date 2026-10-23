"""Shell text pre-pass: drop heredoc bodies and comments before lexing."""

import re

_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([A-Za-z0-9_.-]+))")


_OPENERS = (("$((", "(("), ("((", "(("), ("$[", "["), ("${", "{"))
_CLOSERS = {"((": "))", "(": ")", "[": "]", "{": "}"}


def _skip_body(text: str, i: int, pending: list) -> int:
    """From the start of a line, skip each pending heredoc body through its terminator."""
    for tabs, tag in pending:
        while i < len(text):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            line = text[i:end].lstrip("\t") if tabs else text[i:end]
            i = end + 1
            if line == tag:
                break
    return min(i, len(text))


def strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc body lines (up to and including each terminator) and shell comments.

    A comment is an unquoted `#` starting a word, through end of line (`x#y`, `$#`,
    `${#x}`, quoted `#` and `#` after an escaped space are not comments). Backslash-newline
    line continuations outside single quotes are joined.

    One pass over the whole text; quote, escape, comment and arithmetic/brace state carry
    across newlines. `<<` counts only in plain command context; `<<<` is ignored. An
    unterminated heredoc drops the rest. If the text ends inside an unclosed quote or
    bracket construct, the original text is returned unchanged.
    """
    text = command
    out: list[str] = []
    stack: list[str] = []
    pending: list = []
    start = i = 0
    while i < len(text):
        top = stack[-1] if stack else None
        ch = text[i]
        if top == "'":
            if ch == "'":
                stack.pop()
        elif top == "$'" and ch == "\\":
            i += 1
        elif top == "$'" and ch == "'":
            stack.pop()
        elif top == "$'":
            pass
        elif top != '"' and ch == "'" and i > 0 and text[i - 1] == "$" and not _escaped(text, i - 1):
            stack.append("$'")
        elif ch == "\\" and text.startswith("\n", i + 1):
            out.append(text[start:i])  # line continuation: join the two lines
            i = start = i + 2
            continue
        elif ch == "\\":
            i += 1
        elif top == '"' and ch == '"':
            stack.pop()
        elif top in _CLOSERS and text.startswith(_CLOSERS[top], i):
            i += len(_CLOSERS[top]) - 1
            stack.pop()
        elif top in ("((", "(") and ch == "(":
            stack.append("(")
        elif top != '"' and ch in "'\"":
            stack.append(ch)
        elif any(text.startswith(op, i) for op, _ in _OPENERS if top != '"' or op[0] == "$"):
            op, kind = next(p for p in _OPENERS if text.startswith(p[0], i))
            stack.append(kind)
            i += len(op) - 1
        elif top is not None:
            pass
        elif ch == "#" and _word_start(text, i):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            out.append(text[start:i])
            start, i = end, end - 1
        elif text.startswith("<<<", i):
            i += 2
        elif text.startswith("<<", i) and (match := _HEREDOC.match(text, i)):
            tag = next(g for g in match.groups()[1:] if g is not None)
            pending.append((match.group(1) == "-", tag))
            i = match.end()
            continue
        elif ch == "\n" and pending:
            out.append(text[start : i + 1])
            i = start = _skip_body(text, i + 1, pending)
            pending = []
            continue
        i += 1
    if stack:
        return command
    out.append(text[start:])
    return "".join(out)


def _word_start(text: str, i: int) -> bool:
    """True when text[i] starts a word: at the start, or after an unescaped separator."""
    return i == 0 or (text[i - 1] in " \t\n;&|()" and not _escaped(text, i - 1))


def _escaped(text: str, i: int) -> bool:
    """True when text[i] is preceded by an odd number of backslashes."""
    count = 0
    while i - count - 1 >= 0 and text[i - count - 1] == "\\":
        count += 1
    return count % 2 == 1


_VAR_REF = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_ASSIGN_WORD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)


def expand_known(word: str, env: dict) -> str:
    """Replace $NAME / ${NAME} for names assigned earlier in the chain; others stay as-is."""
    def sub(match):
        name = match.group(1) or match.group(2)
        return env[name] if name in env else match.group(0)
    return _VAR_REF.sub(sub, word)


def track_assignments(words: list[str], env: dict) -> list[str]:
    """Expand known variables in words; a command of only NAME=value words updates env.

    Returns the expanded words, or [] when the command was only assignments. A value that
    still holds `$` or a backtick after expansion makes that name unknown again.
    """
    words = [expand_known(w, env) for w in words]
    matches = [_ASSIGN_WORD.match(w) for w in words]
    if not words or not all(matches):
        return words
    for match in matches:
        name, value = match.group(1), match.group(2)
        if "$" in value or "`" in value:
            env.pop(name, None)
        else:
            env[name] = value
    return []
