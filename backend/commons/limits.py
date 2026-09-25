"""The longest string each buyer-typed field may hold (SR-11).

One place, so the brief, the run request and the reader change cannot drift.
Generous for a real order (the committed briefs use a fraction of each) and
small enough that a 100,000-character `tone` is a 422 at the edge, not a
prompt, a row and a log line.
"""

#: A name, a word or a short phrase: alias, pronouns, dates, occasion, genre,
#: tone, relationship, one trait, one forbidden term.
SHORT_TEXT = 200
#: A sentence or a paragraph: one memory, one mandatory fact, the dedication.
LONG_TEXT = 1_000
#: The free box. Stored whole as one `freetext` fact, never in the premise.
FREE_TEXT = 5_000
#: A profile name; the real check is the allowlist in `config.loader`.
PROFILE = 64
#: A reader change's new reading of one fact.
CHANGE_TO = 1_000
#: An id sent in a body: a brief id, a reader change's fact id.
ID = 64
