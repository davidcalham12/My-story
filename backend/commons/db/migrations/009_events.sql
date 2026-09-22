-- The stream itself, one row per line, as `claude -p` wrote it.
--
-- Everything else in this database is what the stream *revealed*: a stage, a
-- call, a score. Until this table the stream was read once and thrown away, and
-- the record of a run was a reconstruction of it. That is how "which gate did
-- this run actually run" had to be guessed back from the scores (008), and
-- guessed wrong.
--
-- `payload` is the untouched line: key order, spacing, fields this reader does
-- not understand. `seq` is dense per run, so `Last-Event-ID: n` on the SSE
-- stream means "everything after row n" with nothing to interpret. A run is
-- judged by the stream it ran; this is that stream.
CREATE TABLE events (
  run_id  TEXT    NOT NULL REFERENCES runs(id),
  seq     INTEGER NOT NULL,
  ts      TEXT    NOT NULL,              -- when the backend read the line
  type    TEXT    NOT NULL,              -- the line's own `type`, or 'unknown'
  payload TEXT    NOT NULL,              -- the raw line
  PRIMARY KEY (run_id, seq)
) STRICT;
