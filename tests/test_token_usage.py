import importlib.util
import json
import unittest
from pathlib import Path

from tests.helpers import AfcTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "docs/measurements/token_usage.py"


def _load():
    spec = importlib.util.spec_from_file_location("token_usage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _line(mid, i, cc, cr, out, kind="assistant"):
    usage = {"input_tokens": i, "cache_creation_input_tokens": cc,
             "cache_read_input_tokens": cr, "output_tokens": out}
    return json.dumps({"type": kind, "message": {"id": mid, "usage": usage}})


class TokenUsageTests(AfcTestCase):
    def test_sums_fresh_tokens_and_finds_peak_context(self):
        path = self.tmp / "s.jsonl"
        path.write_text("\n".join([
            _line("a", 2, 100, 50, 10),
            _line("b", 2, 20, 150, 5),
            json.dumps({"type": "user", "message": {"content": "hi"}}),
        ]), encoding="utf-8")
        r = _load().measure(path)
        self.assertEqual(r["turns"], 2)
        self.assertEqual(r["peak_context"], 172)  # 2 + 20 + 150
        self.assertEqual(r["fresh_tokens"], (2 + 100 + 10) + (2 + 20 + 5))
        self.assertEqual(r["cache_read_tokens"], 200)

    def test_repeated_message_counts_once(self):
        path = self.tmp / "s.jsonl"
        path.write_text("\n".join([_line("a", 2, 100, 50, 10), _line("a", 2, 100, 50, 10)]), encoding="utf-8")
        r = _load().measure(path)
        self.assertEqual((r["turns"], r["fresh_tokens"]), (1, 112))

    def test_skips_bad_lines(self):
        path = self.tmp / "s.jsonl"
        path.write_text("not json\n" + _line("a", 1, 1, 1, 1) + "\n{}\n", encoding="utf-8")
        self.assertEqual(_load().measure(path)["turns"], 1)
