# U3b — outline, the audit of the commission (FLOW-3, second half)

One unit: the plan is checked against canon before a word of it is written. Read
`.claude/skills/storymaker/SKILL.md` first — the agents' tool boundary, the
logging duties and the ceiling are there and are not repeated here.

**Why this is half a unit.** FLOW-3 used to be one process and ended at 109,722
tokens against a ceiling of 100,000. See `units/outline-write.md` for the
arithmetic. What matters here is that `outline.md` is already on disk and you
read it from there, because nothing carries between units but disk.

**Your unit ends when `critiques/outline.audit.json` exists.** You may correct
`outline.md` — that is the point of auditing before anyone writes from it — but
the audit file is what you owe.

## 1. Audit the commission before anyone writes it

Dispatch `science-critic` with the outline entries and `bible/world.md`, asking
whether every beat can happen **without breaking a rule**. There is no draft; it
is judging the commission, not prose.

This is the cheapest check in the pipeline and it earns its place. Run against a
real outline it cost $0.07–$0.13 and found two defects the full six-characteristic
gate never caught across three attempts and a patch: a beat that had a field-team
member set a permanent RECOVERED line the rules reserve to the duty controller,
and a beat that fired an automatic callout at exactly twenty minutes where the
rule says more than twenty. Both were cheap to fix in the outline and expensive
to discover in a chapter.

**Ask for a finding per violated clause, not per beat.** A rule that says who may
act, on what evidence, and within what window is three clauses, and a beat can
satisfy the window while using evidence the rule never admitted.

**Also ask which rules are AMBIGUOUS, and treat that as a finding.** This is not
padding. A run deadlocked on a rule that read two ways: the science critic held
that a correction line needs its own two confirmations, three separate audits
held that it inherits the original line's, and both readings are defensible from
the same sentence. Two critics then pulled in opposite directions on the same
draft for three attempts and the chapter could not pass. An ambiguous rule does
not fail loudly; it fails as a disagreement nobody can arbitrate, and the place
to fix it is `bible/world.md`, before FLOW-4.

Where a beat is impossible or a rule reads two ways, dispatch `plot-architect`
again with that finding, or fix the rule, and **do not leave a commission that
contradicts canon for U4 to discover.** A chapter cannot be redrafted into
obeying a rule its own outline told it to break, and by then the run is spending
three attempts and a patch per chapter to find that out.

A rule corrected in `bible/world.md` is a Bible whose rows are stale, so re-run
`python -m backend.bible.ingest <run_dir>` after any such correction — it is
idempotent. An outline rewritten here is still an outline U4 must be able to
split: re-check that it yields `novel.chapters` entries on
`### Chapter N — Title` before you finish.

## 2. Write the audit down in this exact shape

`critiques/outline.audit.json`, and **these keys, spelled this way**:

```json
{"stage": "FLOW-3", "agent": "science-critic", "ts": "<a real clock reading>",
 "verdict": "clean" | "defects",
 "violations":  [{"chapter": 3, "beat": 4, "rule": "R1", "clause": "...",
                  "severity": "high", "claim": "...", "fix": "...",
                  "arbitration": "UPHELD ... | OVERRULED ..."}],
 "ambiguities": [{"rule": "R5", "clause": "...", "reading_a": "...",
                  "reading_b": "...", "outline_assumes": "a" | "b" | "neither",
                  "arbitration": "...", "applied": "..."}]}
```

**Both arrays always, even when empty.** Two real runs wrote this file two
different ways — one used `ambiguities`, the other `ambiguous_rules` beside an
empty `violations` — and a reader that wants to ask "how often does the audit
find something" cannot, because the question has two spellings. v1 wrote its
critiques in three shapes for the same reason: nobody said which. **A contract
nobody stated cannot be enforced, and this is the statement.**

## 3. Record and finish

`critiques/outline.audit.json` is on disk with both arrays present, `outline.md`
still splits into `novel.chapters` entries, and `state.json` and
`logs/agents.jsonl` carry what happened (SKILL.md §6).

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — each chapter is its own unit, and the conductor is already
waiting to start the first.
