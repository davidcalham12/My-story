"""The gate's next move, as a script the orchestrator runs. SPEC-004 A8.

    echo '{"aggregate": 7, "attempt": 3, "patched": true}' \
      | python -m backend.chapters.decide

Prints one JSON object: `action`, `verdict`, `why`. **A rule the orchestrator
cannot invoke is a rule it has to remember**, and the whole point of moving this
out of `SKILL.md` is that remembering is what failed.

It reads stdin rather than argv for the reason everything here does: in v1 a task
was passed as a command-line argument with `shell=True` on Windows, which was
command injection and shipped for about an hour.

**It refuses a payload it cannot read.** A decision script that answers anyway is
worse than one that fails, because the orchestrator would then obey an answer
nothing produced.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

from backend.chapters.domain import (MAX_ATTEMPTS_DEFAULT, THRESHOLD_DEFAULT,
                                     decide)


def main(argv: list[str]) -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("expected a JSON object")
        aggregate = payload.get("aggregate")
        if aggregate is not None:
            aggregate = int(aggregate)
        attempt = int(payload["attempt"])
    except (ValueError, TypeError, KeyError) as exc:
        print(
            f"decide: cannot read the payload ({exc}). Expected "
            f'{{"aggregate": <int|null>, "attempt": <int>, "patched": <bool>}}',
            file=sys.stderr,
        )
        return 2

    decision = decide(
        aggregate=aggregate,
        attempt=attempt,
        max_attempts=int(payload.get("max_attempts") or MAX_ATTEMPTS_DEFAULT),
        patched=bool(payload.get("patched")),
        threshold=int(payload.get("threshold") or THRESHOLD_DEFAULT),
    )
    print(json.dumps(asdict(decision), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
