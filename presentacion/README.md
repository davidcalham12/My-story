# presentacion/

**Idioma: castellano**, con los términos técnicos en inglés.

Presentación formal al cliente ficticio *Páginas de Regalo S.L.*, con la
identidad de Qaracter (DM Sans, naranja #FF7932, azul #1E2D3D).

## Contenido

| fichero | qué es |
|---|---|
| `storymaker-deck.pdf` | el deck principal, 19 slides en pirámide (respuesta, tres razones, cierre), en PDF, impreso desde las slides de Claude Design el 25-09 |
| `storymaker-deck.pptx` | el mismo deck en formato editable, con las notas del orador |
| fuente del deck | Claude Design, sistema *Qaracter design FRM*: https://claude.ai/artifact/9YKcBatBGdLkfGVBCJ5JAH (privado; se comparte desde su menú Share) |
| `anexos/anexo-a-arquitectura-harness.pdf` | diagrama del harness: agentes, orquestador, Story Bible, puerta de calidad |
| `anexos/anexo-b-tla-spec.pdf` | especificación TLA+ (`tla/Harness.tla`), su correspondencia con el código y el resultado de TLC: 18.253 estados, sin errores, y el contraejemplo corregido |
| `anexos/anexo-c-maquina-estados.pdf` | la máquina de estados del harness |
| `anexos/anexo-d-evals-tabla.pdf` | la tabla de evals: cinco briefs × validadores, con números |
| `anexos/anexo-e-esquema-sqlite.pdf` | el esquema SQLite de la Story Bible |
| `anexos/anexo-f-validadores.pdf` | los validadores por tipo y dónde actúa cada uno |
| `anexos/anexo-g-red-team-log.pdf` | casos adversariales probados, quién los detectó y cómo se resolvió |
| `anexos/anexo-h-iteraciones.pdf` | qué cambió tras cada eval o contraejemplo, y por qué |
| `anexos/anexo-i-costes-por-cambio.pdf` | el coste medido de cada cambio (orquestador y agentes, minutos), confirmado en Langfuse, y el margen |
| `anexos/anexo-j-cambio-del-lector.pdf` | la demo del cambio del lector (v3): el hecho, los capítulos afectados, la comprobación de llegada y lo que costó |
| `anexos/anexo-k-seguridad.pdf` | el informe de seguridad: hallazgos, severidad, estado y el commit que los resolvió |
| `anexos/anexo-l-verificacion-y-huecos.pdf` | los huecos declarados de `docs/verification.md` §3 |
| `anexos/anexo-m-decisiones-del-dueno.pdf` | cada decisión posterior a la spec, con las palabras del dueño |
| `anexos/anexo-n-lean-cronologia.pdf` | Lean: los invariantes de la cronología y por qué no se ejecutó |
| `anexos/anexo-o-inspeccion-visual.pdf` | las sesiones de browser MCP (`visual_check`): qué inspeccionó, qué detectó y qué cambió |
| `anexos/anexo-p-juez-y-lectura-humana.pdf` | el juez (seis criterios con justificación) frente a la lectura humana |
| `anexos/anexo-q-claude-code.pdf` | Claude Code en el repo: los 13 agentes y su autoridad, comandos, skills y memoria |
| `anexos/anexo-r-siguientes-pasos.pdf` | lo último construido (specs 006, 007, 008) y el siguiente paso |
| vídeo | la demo grabada; el enlace se añade aquí al subirla |

La novela de ejemplo (10 capítulos, brief 01) está en
`../ejemplos/novela-ejemplo.pdf`, y su versión de 8 capítulos, conservada, en
`../ejemplos/novela-ejemplo-v1-8-capitulos.pdf`. La demo del cambio del lector
(un hecho cambiado, propagado solo a los capítulos 3 y 10, con su página de
novedades) es la v3: `../ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`.

## Email de entrega

Asunto: `[Harness Engineering] Entrega final — David Calderon Hamui`

- Commit final de storyMaker: `https://github.com/davidcalham12/StoryMaker/commit/<hash>`
- Commit final de MyFactory: `https://github.com/davidcalham12/my-factory/commit/<hash>`
- La decisión de diseño, en tres líneas como máximo:

> El escritor de cada capítulo no puede leer los anteriores: su única herramienta devuelve rutas, no contenido. Toda la continuidad pasa por una story bible en SQLite que sabe qué capítulo usa cada dato, y por eso un cambio del lector reescribe solo esos capítulos.

El índice de los anexos, con cómo se generan, está en `anexos/README.md`.
