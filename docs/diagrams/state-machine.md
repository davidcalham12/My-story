# Generation as a state machine (what the TLA+ specification models)

```mermaid
stateDiagram-v2
  [*] --> Configuring
  Configuring --> Planning: brief complete
  Configuring --> Halted: brief rejected
  Planning --> Writing
  Writing --> Validating: draft of chapter n
  Validating --> Writing: fail and retries below 3
  Validating --> Checkpoint: pass
  Validating --> Halted: fail after patch
  Checkpoint --> Writing: n below chapters
  Checkpoint --> Published: n equals chapters
  Published --> Writing: reader change, affected chapters only, new version
  Writing --> Halted: budget
  Halted --> [*]
  Published --> [*]
```

Safety: no published version contains a chapter that did not pass; resuming from a checkpoint neither duplicates nor loses a chapter; a previous version is never modified; retries never exceed the limit. Liveness: every generation ends in Published or Halted.
