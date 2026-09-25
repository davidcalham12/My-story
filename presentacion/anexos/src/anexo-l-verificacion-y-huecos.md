# Anexo L — Verificación: garantías y huecos declarados

`docs/verification.md` clasifica cada garantía con su letra (T test, A análisis,
I inspección, D demostración, U no verificable) y un nivel de criticidad. Su §3 lista
lo que **no** está verificado, y por qué es una decisión:

> Un hueco listado es una decisión. Un hueco no listado es un defecto.

| § | hueco declarado |
|---|---|
| 3.1 | patch_then_halt is demonstrated, not tested — and G6 is critical |
| 3.2 | The outline audit is a judgement, and G11 is important |
| 3.3 | Cost has no split by agent |
| 3.4 | The ceiling cannot be reserved before a call |
| 3.5 | The packets the ceiling is about are measured as a total, not as a packet |
| 3.6 | Four of the six gate scores are a model's judgement |
| 3.7 | An agent cannot measure its own work |
| 3.8 | A critic can raise a false finding |
| 3.9 | Nobody measures the quality of the prose |
| 3.10 | A false prose finding damages a correct chapter |
| 3.11 | A run's procedure can change while it is running |
| 3.12 | The procedure in SKILL.md cannot be tested at $0 |
| 3.13 | The archive is as complete as the orchestrator's writing was |
| 3.14 | A run that dies mid-flight archives nothing |
| 3.15 | Two memory layers are built, tested, and not running |
| 3.16 | An interrupted run is not resumed |
| 3.17 | The writer's isolation is asserted from a file, not observed at runtime |
| 3.18 | Repairing one characteristic can break another |
| 3.19 | The backend writes no log file; the database is the log |
| 3.22 | GET /api/runs/{id}/events with an unknown id fails inside the generator |
| 3.21 | Whether --max-budget-usd binds under a subscription is unknown |
| 3.20 | The import CLI on a fresh database labels v2 runs as v1 history |
| 3.23 | The recipient's alias is put in by code, after the gate |
| 3.24 | A unit that is stopped leaves no cost in the ledger |
| 3.25 | A redo overwrote the stream of the pass it redid (before SPEC-EXAM-008) |

25 huecos declarados, cada uno con qué no se verifica, por qué se acepta, el
alcance del daño y cómo nos enteraríamos.
