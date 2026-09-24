---
description: Regenerate the eval table from the validations rows - no model call, no cost
---

Rebuild `evals/results.md` from what the code and the database already hold.

1. `python evals/run_eval.py` — FLOW-0 over the five committed briefs in
   `evals/briefs/` (free: it is `backend/brief/domain.py`), and the novel half
   read from the `validations` table.
2. Check the rows a reader will look for: 03 and 05 refused at FLOW-0 **for the
   reason they were written**; 04's injection kept as a `freetext` row and
   absent from the prose; every validator that did not run says why.
3. Do not launch a novel to fill a gap. An eval run costs money and needs the
   owner's approval; say what is missing instead.
