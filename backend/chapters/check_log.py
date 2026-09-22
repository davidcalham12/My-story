"""The call log's timestamps — real, ordered, and honest about which are which.

    python -m backend.chapters.check_log output/<slug>

SPEC-007 §8 point 2 asks the procedure to record a real `ts` per call. What the
first real v2 run recorded was 3 `measured` rows and 47 `derived_from_duration`
— the orchestrator wrote the time it could compute, labelled it, and moved on.
That label is the whole difference between a figure and a guess, and this check
exists so the count is read rather than assumed (`verification.md` §3.12, the
procedure half nothing at $0 can hold).

It fails only on what no honest log can have: a `ts` that does not parse, or one
that runs backwards. A derived timestamp is reported, not refused.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def _parse(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def check(run_dir: Path) -> dict:
    log = run_dir / "logs" / "agents.jsonl"
    if not log.is_file():
        return {"rows": 0, "monotonic": None, "ts_source": {}, "problems": ["no logs/agents.jsonl"]}
    problems: list[str] = []
    sources: Counter[str] = Counter()
    previous: datetime | None = None
    rows = 0
    monotonic = True
    for i, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"row {i}: not JSON")
            continue
        rows += 1
        # Absent is absent — a row that names no provenance is not `measured`.
        sources[str(row.get("ts_source") or "absent")] += 1
        ts = _parse(row.get("ts"))
        if ts is None:
            problems.append(f"row {i}: ts {row.get('ts')!r} does not parse")
            monotonic = False
            continue
        if previous is not None and ts < previous:
            problems.append(f"row {i}: ts {row.get('ts')} is earlier than the row before it")
            monotonic = False
        previous = ts
    return {"rows": rows, "monotonic": monotonic, "ts_source": dict(sources), "problems": problems}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <run_dir>", file=sys.stderr)
        return 2
    report = check(Path(argv[1]))
    report["note"] = ("`derived_from_duration` is honest provenance, not a defect; "
                      "what fails is a timestamp that does not parse or runs backwards.")
    print(json.dumps(report, indent=2))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
