"""PLAN-007 6.3 — FR-CFG-1: a run carries a hash of what it actually ran with.

The snapshot is already stored per run. The hash is what lets two runs be said
to have run the same configuration without diffing two JSON blobs by eye.
"""

import json

from backend.commons.config import loader
from backend.commons.db import repository as repo
from backend.runs import repository as read_repo


def test_the_same_resolved_config_hashes_the_same():
    a = loader.resolve("tiny")
    b = json.loads(json.dumps(a))          # a copy through serialisation
    assert loader.config_hash(a) == loader.config_hash(b)
    assert len(loader.config_hash(a)) == 16
    # Key order is not configuration.
    reordered = dict(reversed(list(a.items())))
    assert loader.config_hash(reordered) == loader.config_hash(a)
    # A different number is a different configuration.
    b["budget"]["max_cost_usd"] = a["budget"]["max_cost_usd"] + 1
    assert loader.config_hash(b) != loader.config_hash(a)
    assert loader.config_hash(loader.resolve("tiny")) != loader.config_hash(loader.resolve("stress"))


def test_detail_exposes_the_hash_of_the_stored_snapshot(db):
    snapshot = loader.resolve("tiny")
    repo.create_run(db, run_id="r1", slug="s1", premise="A premise long enough.",
                    profile="tiny", tone=None, snapshot=snapshot)
    run = read_repo.get_run(db, "r1")
    assert run["config_hash"] == loader.config_hash(snapshot)
    # Computed from what was stored, not from what the config says today.
    db.execute("UPDATE runs SET config_snapshot = '{\"changed\": true}' WHERE id = 'r1'")
    assert read_repo.get_run(db, "r1")["config_hash"] == loader.config_hash({"changed": True})
