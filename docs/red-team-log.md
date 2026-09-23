# Red-team log

Adversarial cases tried, which validator caught them (or did not), and how each was resolved.

| # | case | caught by | resolution |
|---|---|---|---|
| 1 | a task passed to the CLI as a command-line argument with a shell (v1) — command injection for about an hour | nothing; found by reading | the prompt goes on stdin, never as an argument, no shell; a test asserts a hostile premise appears in no argument |
| 2 | path traversal in the v1 panel's file server | nothing; found by testing | containment checked on the normalised path; v2 serves no file by client path, pinned by a route test |
| 3 | a malformed critic reply counted as a pass | nothing at the time | excluded from the minimum, tested |
| 4 | the orchestrator disobeyed its own gate on a real run (a chapter promoted at 5; another with a critic silent) | **conformance audit**, within minutes | the decision moved to code; promotion refuses; detection, not prevention, stated as a gap |
| 5 | the orchestrator on a cheaper model ignored the named agents and used a generic agent holding every tool | the dispatch record (subagent type per call) and an empty critiques folder | orchestrator stays on the session model; the run is kept as evidence |
| 6 | secrets pasted into a chat | policy | credentials are read only from the environment; the example environment file has names, no values |
| 7 | brief 04: prompt injection in the buyer's free text plus client forbidden terms | interviewer (free text stored as untrusted material, never an instruction) and the forbidden-words guardrail | result recorded here when the eval runs |
| 8 | brief 05: memories that make an age impossible | Lean chronology invariant if the tooling installs, else the judge | result recorded here when the eval runs |
| 9 | stopping the server left its orchestrator process alive: three orphaned runs kept writing unrequested novels for 25–29 minutes each, and the startup sweep marked their rows halted, so **the database said the run was over while the process was still billing** | nothing automatic; found by counting the output folders and the live processes | the orphans were killed by hand; recorded as NovaForge verification §3.23 (commit 295bf75); a server that stops must stop its child, and a launch must check for a live orchestrator first — declared, not fixed before Friday |
