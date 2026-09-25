# Project memory — storyMaker

What an agent new to this repo should know before it acts, each learned from a
run that went wrong. One line per memory; the file holds the reason and where
the evidence lives. `CLAUDE.md` is the entry point; this is what it cannot say
in one screen.

- [The writer's isolation is a capability](writer-isolation.md) — `chapter-writer` holds only `Glob`; never add `Read`
- [The orchestrator is the bill](orchestrator-cost.md) — ~92 % of a novel's cost; Sonnet, never Haiku, and check `modelUsage`
- [Absent is never zero](absent-never-zero.md) — a figure nobody measured is NULL and says so
- [The recipient's name goes in by code](alias-by-code.md) — models write a placeholder; `personalise` puts the alias in at publication
- [A reader change must arrive](reader-change-arrival.md) — the gate does not check a changed fact; the arrival check does
- [Operating rules that each cost a run](operations.md) — one server per database, suite alone before a push, prompt on stdin
- [Who approves spending](approvals.md) — only the owner's words, in the session that spends
