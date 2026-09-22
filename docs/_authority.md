# Authority

Which document wins when two disagree — **by type of statement**, never by age.
`coherencia-docs` reads this table in place of its own.

| statement type | wins | others |
|---|---|---|
| what a term means | `docs/definitions.md` | use it, never redefine |
| how the domain works | `docs/domain-knowledge.md` | apply it |
| technical decisions, agents, process, limits | `docs/architecture.md` | reference it |
| operating rules for the coding agent | `AGENTS.md` | invoke them |
| Claude Code specifics (commands, permissions) | `claude.md` | derived from `AGENTS.md` |
| verification method and T/A/I/D/U letter per guarantee | `docs/verification.md` | derived: loses to `architecture.md` on facts |
| requirements of one deliverable | `specs/SPEC-*.md` | derived from `architecture.md` |
| implementation order | `specs/PLAN-*.md` | derived from its SPEC |

Two consequences worth stating:

- **`verification.md` is authority on the method and subordinate on the facts.**
  It decides what T, A, I, D and U mean and which letter a guarantee has earned.
  It does not decide what the architecture is; when the two disagree about a
  fact, `verification.md` is what gets corrected.
- **A spec is derived.** Where `SPEC-*.md` and `architecture.md` disagree, the
  work stops and the two are reconciled before a plan is written — the spec says
  so itself (SPEC-001 §12).
