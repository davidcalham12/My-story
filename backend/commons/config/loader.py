"""Loading the spec and the config. The orchestrator holds no literals.

A chapter count, a threshold or a stage order written into Python is a second
source of truth, and the two disagree within a month. Everything structural
comes from `specs/flow.yaml`; every number comes from `config/`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config"
SPECS = ROOT / "specs"


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Overlay key by key.

    A profile is partial: it states what it changes and nothing else. Replacing
    whole sections is how a three-chapter run once inherited a twelve-chapter
    Story Bible and spent every chapter introducing canon it had no room for.
    """
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


@lru_cache
def load_flow() -> dict[str, Any]:
    # Imported here rather than at module scope: everything else in this file is
    # JSON, and a missing YAML parser should break loading the flow spec, not
    # loading the pricing table.
    import yaml

    return yaml.safe_load((SPECS / "flow.yaml").read_text(encoding="utf-8"))


@lru_cache
def load_base() -> dict[str, Any]:
    return json.loads((CONFIG / "novel.config.json").read_text(encoding="utf-8"))


@lru_cache
def load_pricing() -> dict[str, Any]:
    return json.loads((CONFIG / "pricing.json").read_text(encoding="utf-8"))


PROFILE_NAME = re.compile(r"[a-z0-9-]+")


def profile_names() -> list[str]:
    """The profiles that exist: the stems of `config/profiles/*.json`."""
    return sorted(p.stem for p in (CONFIG / "profiles").glob("*.json"))


def check_profile(name: str) -> str:
    """`name` if it is a profile on disk, else a `ValueError` a person can read.

    A profile arrives in a request body and becomes a filename (SR-04), so it is
    an allowlist, not a path: the strict pattern first, so nothing with a
    separator or a `..` is ever joined into a path, then existence.
    """
    if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name)             or name not in profile_names():
        raise ValueError(f"unknown profile {name!r}; the profiles are: "
                         f"{', '.join(profile_names())}")
    return name


def load_profile(name: str) -> dict[str, Any]:
    path = CONFIG / "profiles" / f"{check_profile(name)}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(profile: str) -> dict[str, Any]:
    """The merged configuration a run actually runs with."""
    return _merge(load_base(), load_profile(profile))


def config_hash(snapshot: dict[str, Any]) -> str:
    """Sixteen hex characters over the canonical JSON of a resolved config.

    Key order is not configuration, so the keys are sorted first. Two runs with
    the same hash ran the same numbers; a run whose hash differs from today's
    `resolve(profile)` ran an older one, and says so without a diff (FR-CFG-1).
    """
    import hashlib

    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def prompt_for(feature: str, agent: str) -> str:
    """An agent's prompt, from disk. Agents do not read disk; this does."""
    path = ROOT / "backend" / feature / "prompts" / f"{agent}.md"
    text = path.read_text(encoding="utf-8")
    # The header comment records the model and v1's tool list; it is provenance
    # for a human, not instruction for a model.
    if text.startswith("<!--"):
        text = text.split("-->", 1)[1].lstrip()
    return text
