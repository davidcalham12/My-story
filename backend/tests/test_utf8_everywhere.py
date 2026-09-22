"""PLAN-007 6.4 — NFR-7: UTF-8 explicit on every write and read (SPEC-007 C4).

On Windows the default text encoding is cp1252. A file written without naming
its encoding is a file that reads differently on the next machine, and the
sheets, the critiques and the cost records all travel.
"""

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# A text I/O call, with everything up to its closing paren (calls here never
# nest another call with a paren-heavy argument; the regex is deliberately
# simple and the test is deliberately strict).
CALLS = re.compile(r"\.(write_text|read_text)\(|\bopen\(", re.M)


def _calls(source: str):
    for m in CALLS.finditer(source):
        start = m.start()
        depth, i = 0, m.end() - 1
        while i < len(source):
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield source[start:i + 1], source.count("\n", 0, start) + 1


def test_every_text_io_call_outside_tests_names_utf8():
    offenders = []
    for path in BACKEND.rglob("*.py"):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        for call, line in _calls(path.read_text(encoding="utf-8")):
            if "open(" in call and ('"rb"' in call or "'rb'" in call or '"wb"' in call or "'wb'" in call):
                continue  # binary: no encoding applies
            if "utf-8" not in call and "utf8" not in call:
                offenders.append(f"{path.relative_to(BACKEND)}:{line}: {call[:60]!r}")
    assert not offenders, "\n".join(offenders)
