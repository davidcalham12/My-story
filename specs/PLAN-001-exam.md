# PLAN-001 — storyMaker in thirty-six hours

status: approved
date: 2026-09-23
implements: docs/spec.md (SPEC-EXAM-001, approved 2026-09-23)
approved_by: David Calderon — in chat, 2026-09-23: "acepto y apruebo tus recomendaciones y todo"; written at his instruction
executes: novaforge-05 (build, runs, commits) · reviews: the session "Novaforge continuación con repositorios" (this plan's author) · decides: the owner
clock: Wednesday 2026-09-23 17:00 UTC → Friday 2026-09-25 07:00 UTC

Every phase: tests first where a test can exist, one commit, announce before
committing, `git pull --rebase` before. The harness's `AGENTS.md` still
governs. Phases are ordered by **what passes the exam first**: a novel exists,
then the validators score it, then five briefs are measured, then the
documents say how. Formal methods and the deck come last and are cut first.

## Part 1 — Wednesday evening (until ~23:00 UTC)

### E1 — the exam profile and the first novel (novaforge-05)
- `config/profiles/exam.json`: 10 chapters; `words_per_chapter` 1000/1250/1500; `tolerance_pct` 10; `bible` as `medium`; `context.max_summary_words` 260; `budget.max_cost_usd` 15.0 (Haiku; adjusted after this run). Test: `test_db_and_tokens.py` profile tests pass with the new profile listed.
- The README's example brief as `evals/briefs/01-hijo.json` (a fictional recipient; no real person).
- Launch the first `exam` run through the backend with the example brief's premise. It is the example novel and the cost reference. Record cost, minutes, attempts.

### E2 — `Brief`, the interviewer, FLOW-0 (novaforge-05)
- Tests: `test_brief.py` — missing field → `incomplete` with questions; age 8 + tone in {`novela negra adulta`, `erótico`, `thriller violento`} → `contradiction`; free text never enters `Brief` fields, only `facts` with `source=freetext`; schema rejects unknown fields.
- Code: `backend/brief/models.py` (`Brief`: recipient alias, age, traits, memories, genre, tone, length, forbidden terms, mandatory facts), `domain.py` (rules), `router.py` (`POST /api/briefs`), `.claude/agents/interviewer.md` (`model: haiku`, `tools: Glob`; extracts, asks for what is missing, never decides), `SKILL.md` §FLOW-0.

### E3 — story bible tables and ingest (novaforge-05)
- Tests: `test_story_bible.py` — migration 010 creates the tables with their CHECKs; `ingest` on `output/lighthouse-keeper-ledger/` yields ≥ 3 characters, ≥ 4 chronology rows, facts from mysteries; `fact_usage` for chapter 1 names the characters that appear in it.
- Code: `010_story_bible.sql`, `backend/bible/ingest.py`, `backend/chapters/fact_usage.py`; `SKILL.md`: FLOW-2 calls `ingest`, FLOW-4 "Record it" calls `fact_usage` on promotion.

## Part 2 — Thursday morning (07:00 → 13:00 UTC)

### E4 — guardrail, audit log, the two hooks (novaforge-05)
- Tests: `test_policy.py` — one hit per level; `Ándres`/`andres`; `perros`→`perro`; a hit writes `audit_log`; the hook scripts print JSON and exit non-zero on a hit.
- Code: `backend/policy/{forbidden.py, audit.py}`, migration `011_policy.sql` (tables + global seed), `.claude/hooks/validate-chapter.py`, `.claude/hooks/policy.py`, `.claude/settings.json` `PostToolUse` matcher on `Write` under `output/*/chapters/`; `SKILL.md`: a hit is a sheet finding of the `forbidden_words` validator; exhausted → `halted: policy`.

### E5 — judge and `mandatory_facts` at the publish gate (novaforge-05)
- Tests: `test_judge.py` — the six-criterion JSON validates; a missing justification is rejected; `mandatory_facts` reports the uncovered fact by id.
- Code: `.claude/agents/judge.md` (`haiku`, `Glob`), `backend/publish/judge.py` (schema + storage in `validations`), `backend/publish/mandatory.py`; `SKILL.md` FLOW-6 runs both before assembling.

### E6 — PDF and versions (novaforge-05)
- Tests: `test_pdf.py` — the HTML has the cover with the dedication, an index with one anchor per chapter, a sheet with one link per character to its first chapter; `versions` row per publish; v2 keeps v1's files.
- Code: `backend/publish/pdf.py` (HTML → `dist/v<N>/novel.html` → Playwright print → `novel.pdf`), migration `012_versions.sql`, `backend/versions/change.py` (`--fact --to`: `fact_usage` → chapters → `claude -p` with the reader-change prompt → gate → new version → PDF with the "what changed" page). `pip install playwright` + `playwright install chromium` (skill `playwright` first).
- `ejemplos/novela-ejemplo.pdf` from the E1 run.

## Part 3 — Thursday afternoon (13:00 → 19:00 UTC)

### E7 — evals (novaforge-05 runs; the reviewer writes briefs 02–05)
- Briefs: 02 pareja/aniversario; 03 missing data + age/tone contradiction; 04 adversarial free text with injection and client forbidden terms; 05 memories with dates that make an age impossible.
- `backend/evals/run.py`: sequential `POST /api/briefs` → run → validators → `validations`; `evals/results.md` generated: brief × validator, pass/fail/value; cost per novel from `cost.json`.
- Tuning: one change to `chapter-writer`'s personalisation instruction; brief 01 re-run; before/after in `docs/iterations.md` with the prompt version (git sha, and the Langfuse prompt version).
- Langfuse export after each novel: `tools/export_to_langfuse.py` (sessions, traces per version, spans per call, scores, prompts). `LANGFUSE_BASE_URL` = US.

### E8 — reader-change demo and human review
- One reader change on the example novel ("the dog is called Nala" or equivalent from brief 01) → v2 PDF. Recorded step by step in `docs/iterations.md`; this is the demo.
- The owner reads one complete novel with the rubric (Thursday night); scores beside the judge's.

## Part 4 — Thursday evening (19:00 → 24:00 UTC)

### E9 — formal methods, conditional
- `backend/formal/lean_export.py` → `lean/Chronology.lean` (structures, concrete lists, two theorems by `decide`); `lake build` if `elan` installed; else the reason.
- `tla/Harness.tla`, `Harness.cfg`; TLC if a JDK installed; else the reason. README mapping table either way.

### E10 — `/docs`, browser MCP, CLAUDE.md, skills (reviewer writes, novaforge-05 checks facts)
- `.claude/mcp.json` with Playwright MCP; one documented session on `dist/v1/novel.html` → `docs/browser-mcp.md`.
- `docs/trade-offs.md`, `explainers/`, `diagrams/`, `iterations.md`, `red-team-log.md`, `verification.md` extended, `skills.md`, `subagents.md`; `CLAUDE.md` rewritten; `.env.example`; `my-factory` updated with every skill and link.

### E11 — presentation (reviewer, Claude Design)
- Deck on the Qaracter design FRM system: cover (Qaracter → fictional client, date, owner), problem, configuration and reading, harness architecture, validation/evals/observability (table from E7, judge, Lean/TLC state, tuning, a Langfuse trace), guardrails, **budget slide** from the measured Haiku costs, demo and close, back cover; annexes: architecture, TLA+, evals table, SQLite schema, red-team log. PDF + PPTX in `presentacion/` with its README.

## Part 5 — Friday 06:00 → 07:00 UTC
- The owner records the video and commits it or its link under `presentacion/`.
- Final commits of both repos; the email with the two commit links and the one sentence (candidate: *the chapter writer cannot read earlier chapters, so the context never grows and chapter 10 costs what chapter 1 costs; all continuity runs through a story bible in SQLite that knows which chapter uses each fact*).

## Part 6 — Cuts, in the order they are taken if time runs out
1. TLA+ (E9 second half) → specification written, TLC not run, reason stated.
2. Lean (E9 first half) → export written, `lake build` not run, reason stated.
3. Tuning iteration → one brief, before/after on the judge score only.
4. Briefs 04 and 05 → three briefs measured, two written and declared not run.
5. Annexes of the deck → the ten mandatory slides only.

Nothing above the line of the five mandatory evidences (evals table, measured
cost, reader-change demo, `/docs`, example PDF) is cut.

## Part 7 — Gaps this plan leaves
As `docs/spec.md` §7, plus: the `exam` profile's budget ceiling is a guess until E1 measures a Haiku run; the hooks' firing inside Claude Code is demonstrated, not unit-tested.
