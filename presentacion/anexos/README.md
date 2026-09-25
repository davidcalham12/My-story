# Anexos de la presentación

**Idioma: castellano**, con los términos técnicos en inglés. Cada anexo es un PDF
individual. Los anexos I en adelante se generan desde el repositorio y su base de
datos con `python tools/build_annexes.py`, así que sus cifras no pueden separarse del
código que describen; su texto fuente está en `src/`. A–H se conservan como se
produjeron.

| anexo | fichero | contenido |
|---|---|---|
| A | [`anexo-a-arquitectura-harness.pdf`](anexo-a-arquitectura-harness.pdf) | Arquitectura del harness: capas, agentes y flujo |
| B | [`anexo-b-tla-spec.pdf`](anexo-b-tla-spec.pdf) | Especificación TLA+ y resultado de TLC |
| C | [`anexo-c-maquina-estados.pdf`](anexo-c-maquina-estados.pdf) | Máquina de estados del harness |
| D | [`anexo-d-evals-tabla.pdf`](anexo-d-evals-tabla.pdf) | Tabla de evals: brief × validador |
| E | [`anexo-e-esquema-sqlite.pdf`](anexo-e-esquema-sqlite.pdf) | Esquema SQLite de la Story Bible |
| F | [`anexo-f-validadores.pdf`](anexo-f-validadores.pdf) | Validadores y dónde actúan |
| G | [`anexo-g-red-team-log.pdf`](anexo-g-red-team-log.pdf) | Red-team log |
| H | [`anexo-h-iteraciones.pdf`](anexo-h-iteraciones.pdf) | Registro de iteraciones |
| I | [`anexo-i-costes-por-cambio.pdf`](anexo-i-costes-por-cambio.pdf) | Costes por cambio y margen (Langfuse) |
| J | [`anexo-j-cambio-del-lector.pdf`](anexo-j-cambio-del-lector.pdf) | Demo del cambio del lector (v3) |
| K | [`anexo-k-seguridad.pdf`](anexo-k-seguridad.pdf) | Informe de seguridad |
| L | [`anexo-l-verificacion-y-huecos.pdf`](anexo-l-verificacion-y-huecos.pdf) | Verificación: garantías y huecos declarados |
| M | [`anexo-m-decisiones-del-dueno.pdf`](anexo-m-decisiones-del-dueno.pdf) | Decisiones del dueño tras la spec |
| N | [`anexo-n-lean-cronologia.pdf`](anexo-n-lean-cronologia.pdf) | Lean: invariantes de la cronología |
| O | [`anexo-o-inspeccion-visual.pdf`](anexo-o-inspeccion-visual.pdf) | Inspección visual con browser MCP |
| P | [`anexo-p-juez-y-lectura-humana.pdf`](anexo-p-juez-y-lectura-humana.pdf) | El juez (LLM-as-judge) y la lectura humana |
| Q | [`anexo-q-claude-code.pdf`](anexo-q-claude-code.pdf) | Claude Code en el repo: agentes, comandos, skills y memoria |
| R | [`anexo-r-siguientes-pasos.pdf`](anexo-r-siguientes-pasos.pdf) | Lo último construido y el siguiente paso |

La novela de ejemplo y sus versiones están en `../../ejemplos/`: la v2 completa
(`novela-ejemplo.pdf`), la v1 de 8 capítulos y la v3 del cambio del lector.
