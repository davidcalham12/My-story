---
description: Publish a finished run - personalise, ingest the Bible, print the PDF, record every validator, ask the judge
argument-hint: <run-dir> [--next "<reason>"]
---

Publish `$ARGUMENTS`.

1. `python -m backend.publish.release output/<slug>` publishes v1;
   `python -m backend.publish.release output/<slug> --next "<reason>"` publishes
   the next version and leaves every earlier one intact. In order, it:
   - replaces the recipient placeholder with the brief's alias, by code (the
     model never held the name);
   - ingests the Bible if nothing did;
   - records `fact_usage`;
   - prints the PDF;
   - records every validator in `validations`.
2. Ask the judge — a model call, so say so first:
   `python -m backend.publish.run_judge output/<slug> <n>`. It stores six
   criteria with a justification each, or `not run: <reason>`.
3. Report every validator's row for the version. A `not run` keeps its reason;
   nothing is reported as passed that did not run.
