"""Jev adapter stays off without a key (FC-024)."""

import io
import unittest
from unittest.mock import patch

from afc.jev import evaluate


class JevTest(unittest.TestCase):
    def test_no_key_is_noop(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(evaluate("state", {"q": {"type": "noul", "instructions": "ok?"}}))

    def test_mock_opener(self):
        class Resp:
            def read(self):
                return b'{"model":"jev-latest","answers":{},"usage":{"input_tokens":1,"output_tokens":0}}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=0):
            return Resp()

        out = evaluate("x", {"q": {"type": "noul", "instructions": "?" }}, api_key="k", opener=opener)
        self.assertEqual(out["model"], "jev-latest")


if __name__ == "__main__":
    unittest.main()
