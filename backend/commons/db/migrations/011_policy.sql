-- The words a novel may not carry, and every policy decision taken about one.
--
-- A forbidden term that lives only in the writer's prompt is a term the writer
-- sometimes still writes, and nothing downstream notices: the gate's six
-- characteristics read for contradiction, rules, beats, size, headings and
-- mechanics, and not one of them reads for a word the buyer asked never to see.
-- A gift novel that names the recipient's ex is not a chapter that scored badly;
-- it is a chapter that cannot be given.
--
-- Three levels, because the three have different authors and different
-- lifetimes: `global` is seeded here and holds for every client (the model
-- breaking character, placeholder text left in prose); `client` comes from the
-- brief's `forbidden_terms`; `novel` is added during a run, when a term turns
-- out to be forbidden only for this book.
--
-- `normalised` is what the detector actually compares: casefold, NFKD with the
-- accents stripped, and a trailing plural `s` removed — so `Ándres`, `Andres`
-- and `andres` are one term and `perros` hits `perro`. It is STORED rather than
-- computed per query because the same rule has to reach a term a human typed
-- into a brief and a term this file seeds by hand; `test_policy.py` holds the
-- seeded rows against `forbidden.normalise` so the two cannot drift. A row whose
-- `normalised` was computed by a different rule is a term that is in the table
-- and can never be hit, which is the worst state this table has: it looks
-- configured.
--
-- The primary key is (level, normalised) and not (level, term): two spellings of
-- one term are one row, and the surviving `term` is whichever spelling was
-- entered first, kept because a finding has to quote the term back to a human in
-- a form they recognise.
CREATE TABLE forbidden_words (
  level      TEXT NOT NULL CHECK (level IN ('global', 'client', 'novel')),
  term       TEXT NOT NULL,          -- as a human wrote it, accents and all
  normalised TEXT NOT NULL,          -- what `forbidden.check` compares against
  PRIMARY KEY (level, normalised)
) STRICT;

-- The global level. Not profanity — that is a client's decision and belongs in
-- their brief. These are the ways a generated chapter stops being a novel at
-- all: the assistant answering as itself, and scaffolding text that was never
-- meant to survive a draft. Each has been seen in generated prose.
INSERT INTO forbidden_words (level, term, normalised) VALUES
  ('global', 'lorem ipsum',             'lorem ipsum'),
  ('global', 'placeholder',             'placeholder'),
  ('global', 'ChatGPT',                 'chatgpt'),
  ('global', 'as an AI language model', 'as an ai language model'),
  ('global', 'como modelo de lenguaje', 'como modelo de lenguaje');

-- Every policy decision, whichever way it went.
--
-- A log that holds only hits cannot tell "the policy ran and found nothing" from
-- "the policy never ran", and the second is the one an auditor needs to see. So
-- the hook writes a row on every check and `decision` says which it was. Absent
-- is never zero, including here.
--
-- `run_id` deliberately carries NO foreign key to `runs`. The hook fires on a
-- `Write` inside `output/<slug>/chapters/`, which happens while the run is being
-- driven by the skill and may happen for a run this database has never archived.
-- A constraint there would turn an unrecordable hit into an exception, and the
-- one thing an audit row must never do is fail to be written. It holds the run's
-- id when the slug resolves to one and the slug itself when it does not.
--
-- No primary key: two identical hits a second apart are two facts, not one row
-- written twice.
--
-- `langfuse_trace_id` is NULL until `tools/export_to_langfuse.py` runs, because
-- the export is post-hoc (docs/spec.md §7). NULL means "not exported", which is
-- a different fact from "exported and had no trace".
CREATE TABLE audit_log (
  run_id            TEXT NOT NULL,
  ts                TEXT NOT NULL,
  actor             TEXT NOT NULL,   -- who decided: 'policy-hook', a person
  decision          TEXT NOT NULL CHECK (decision IN ('hit', 'clean', 'override')),
  detail            TEXT NOT NULL,   -- JSON: the hits, or why it was overridden
  langfuse_trace_id TEXT
) STRICT;
