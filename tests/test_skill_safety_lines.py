import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ["afc-start", "afc-setup", "afc-interview", "afc-slice", "afc-deliver"]
PINNED = ROOT / "tests" / "fixtures" / "skill_safety_lines.txt"
MARKERS = re.compile(r"never|must not|always ask", re.I)


def norm(line: str) -> str:
    return " ".join(line.split())


def safety_lines(text: str) -> list[str]:
    return [norm(l) for l in text.splitlines() if MARKERS.search(l)]


def skill_text(name: str) -> str:
    return (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text()


def pinned() -> list[tuple[str, str]]:
    out = []
    for raw in PINNED.read_text().splitlines():
        if raw.strip():
            name, line = raw.split("\t", 1)
            out.append((name, line))
    return out


def missing(texts: dict[str, str]) -> list[tuple[str, str]]:
    have = {n: set(safety_lines(t)) for n, t in texts.items()}
    return [(n, l) for n, l in pinned() if l not in have.get(n, set())]


class SkillSafetyLinesTest(unittest.TestCase):
    def test_pin_covers_every_skill(self):
        self.assertEqual({n for n, _ in pinned()}, set(SKILLS))

    def test_today_every_pinned_line_is_present(self):
        texts = {n: skill_text(n) for n in SKILLS}
        self.assertEqual(missing(texts), [])

    def test_removing_a_line_fails(self):
        texts = {n: skill_text(n) for n in SKILLS}
        name, line = pinned()[0]
        kept = [l for l in texts[name].splitlines() if norm(l) != line]
        texts[name] = "\n".join(kept)
        self.assertEqual(missing(texts), [(name, line)])

    def test_five_skills_total_at_most_14000_bytes(self):
        total = sum(len((ROOT / ".claude" / "skills" / n / "SKILL.md").read_bytes()) for n in SKILLS)
        self.assertLessEqual(total, 14000, f"five skills total {total} bytes")


if __name__ == "__main__":
    unittest.main()
