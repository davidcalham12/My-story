"""Settings.

**There is no `ANTHROPIC_API_KEY` here and there is no SDK in this project.**
Claude Code is the orchestrator; the only access to a model is the user's own
session on this machine. A key would be a second route to the model, which is
exactly what the architecture no longer has.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECORDED = ROOT / "backend" / "tests" / "fixtures" / "recorded-run.stream.jsonl"


@dataclass(frozen=True)
class Settings:
    repo_root: Path = ROOT
    db_path: Path = ROOT / "novaforge.db"
    output_dir: Path = ROOT / "output"
    # The recorded stream stands in for `claude` in tests and in CI. It covers
    # the runner, the parser, the persistence, the SSE and both watchers at $0.
    # What it cannot cover is the procedure in SKILL.md.
    use_recorded_stream: bool = True
    recorded_stream: Path = RECORDED
    budget_ceiling_usd: float = 25.0


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.environ.get("NOVAFORGE_DB", ROOT / "novaforge.db")),
        use_recorded_stream=os.environ.get("USE_RECORDED_STREAM", "true").lower() != "false",
        budget_ceiling_usd=float(os.environ.get("NOVAFORGE_BUDGET", "25")),
    )
