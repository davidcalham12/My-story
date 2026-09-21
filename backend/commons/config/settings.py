"""Settings. Credentials from the environment, never from a file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    db_path: Path = ROOT / "novaforge.db"
    output_dir: Path = ROOT / "output"
    use_mock_engine: bool = True          # the real engine is opt-in, never default
    budget_ceiling_usd: float = 25.0

    @property
    def api_key(self) -> str | None:
        """Read at the moment of use, from the environment alone.

        Never a default in code, never a file, never an argument, never logged.
        In v1 a task was once passed as a command-line argument with `shell=True`
        on Windows, which was command injection and shipped for about an hour.
        """
        return os.environ.get("ANTHROPIC_API_KEY")


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.environ.get("NOVAFORGE_DB", ROOT / "novaforge.db")),
        use_mock_engine=os.environ.get("USE_MOCK_ENGINE", "true").lower() != "false",
        budget_ceiling_usd=float(os.environ.get("NOVAFORGE_BUDGET", "25")),
    )
