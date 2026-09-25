# Anexo Q — Claude Code en el repo: agentes, comandos, skills y memoria

Cómo refleja el repo el uso de Claude Code (`CLAUDE.md`, `.claude/`, `docs/subagents.md`,
`docs/skills.md`).

## Los 13 agentes — su línea `tools:` es su autoridad

| agente | tools | modelo | para qué |
|---|---|---|---|
| bible-critic | Glob | haiku | FLOW-4 gate, SPEC-EXAM-004. Reads one chapter draft once against the Story Bible, the world's rules and its own outline entry, and returns three score |
| chapter-writer | Glob | haiku | FLOW-4. Drafts one chapter from the Story Bible, its own outline entry and a rolling summary — never from a previous chapter's prose. Redrafts when th |
| character-architect | Read, Write | haiku | FLOW-2. Writes the cast, the timeline and the mysteries — bible/characters.md, bible/timeline.md and bible/mysteries.md — against a world that already |
| continuity-critic | Glob | haiku | FLOW-4 gate. Holds one chapter draft against the Story Bible and reports what contradicts it, as JSON with a score and quoted findings. |
| interviewer | Glob | haiku | FLOW-0. Turns what the buyer wrote into the brief's fields and names the ones still empty. Extracts and asks; it decides nothing. |
| judge | Glob | haiku | FLOW-6 publish gate, SPEC-EXAM-001 §2 validator `judge_rubric`. Reads the assembled book once, after every chapter has passed the gate, and scores six |
| outline-critic | Glob | haiku | FLOW-4 gate, LOOP-003 characteristic 3. Holds one chapter draft against the beats its own outline entry assigned it, and reports which are missing or  |
| plot-architect | Glob | haiku | FLOW-3. Writes the outline — acts, a per-chapter tension curve, and the promises made to the reader. The last agent that sees the whole book at once. |
| prose-critic | Glob | haiku | FLOW-4 gate, SPEC-006 characteristic 6. Holds one chapter draft against the writing itself — paragraphs that advance nothing, dialogue any character c |
| publisher | Glob | haiku | FLOW-6. Writes the back-cover synopsis. The manuscript itself is assembled by the orchestrator, not by this agent. |
| science-critic | Glob | haiku | FLOW-4 gate. Holds one chapter draft against the rules the world declared in bible/world.md — whatever kind of rules those are — and reports where it  |
| style-editor | Glob | haiku | FLOW-5. Gives one voice to chapters written in isolation from each other. Normalises presentation only — deliberately unable to rewrite a word. |
| worldbuilder | Read, Write | haiku | FLOW-1. Turns the premise into the rules the story runs on — whatever kind of rules its genre has — and writes bible/world.md. One of only two agents  |

Solo `worldbuilder` y `character-architect` escriben la Biblia; `chapter-writer` solo tiene
`Glob`, así que no puede leer capítulos anteriores. Un test fija cada línea `tools:`.

## Comandos propios (`.claude/commands/`)

| comando | qué hace |
|---|---|
| /publish | Publish a finished run - personalise, ingest the Bible, print the PDF, record every validator, ask the judge |
| /reader-change | A reader changes one fact; only the chapters that use it are rewritten, as a new version |
| /run-eval | Regenerate the eval table from the validations rows - no model call, no cost |
| /status | What is running, what it has spent, and whether it is safe to launch another run |

## Skills del proyecto (`.claude/skills/`)

`fastmcp`, `novaforge`, `storymaker` — más las de proceso y stack listadas en `docs/skills.md`.

## Memoria del proyecto (`.claude/memory/`)

- The writer's isolation is a capability — `chapter-writer` holds only `Glob`; never add `Read`
- The orchestrator is the bill — ~92 % of a novel's cost; Sonnet, never Haiku, and check `modelUsage`
- Absent is never zero — a figure nobody measured is NULL and says so
- The recipient's name goes in by code — models write a placeholder; `personalise` puts the alias in at publication
- A reader change must arrive — the gate does not check a changed fact; the arrival check does
- Operating rules that each cost a run — one server per database, suite alone before a push, prompt on stdin
- Who approves spending — only the owner's words, in the session that spends
