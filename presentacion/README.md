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
| `anexo-a-arquitectura-harness.pdf` | diagrama del harness: agentes, orquestador, Story Bible, puerta de calidad |
| `anexo-b-tla-spec.pdf` | especificación TLA+ (`tla/Harness.tla`), su correspondencia con el código y el resultado de TLC: 18.253 estados, sin errores, y el contraejemplo corregido |
| `anexo-c-maquina-estados.pdf` | la máquina de estados del harness |
| `anexo-d-evals-tabla.pdf` | la tabla de evals: cinco briefs × validadores, con números |
| `anexo-e-esquema-sqlite.pdf` | el esquema SQLite de la Story Bible |
| `anexo-f-validadores.pdf` | los validadores por tipo y dónde actúa cada uno |
| `anexo-g-red-team-log.pdf` | casos adversariales probados, quién los detectó y cómo se resolvió |
| `anexo-h-iteraciones.pdf` | qué cambió tras cada eval o contraejemplo, y por qué |
| vídeo | la demo grabada; el enlace se añade aquí al subirla |

La novela de ejemplo (10 capítulos, brief 01) está en
`../ejemplos/novela-ejemplo.pdf`, y su versión de 8 capítulos, conservada, en
`../ejemplos/novela-ejemplo-v1-8-capitulos.pdf`.

## Email de entrega

Asunto: `[Harness Engineering] Entrega final — David Calderon Hamui`

- Commit final de storyMaker: `https://github.com/davidcalham12/StoryMaker/commit/<hash>`
- Commit final de MyFactory: `https://github.com/davidcalham12/my-factory/commit/<hash>`
- La decisión de diseño, en tres líneas como máximo:

> El escritor de cada capítulo no puede leer los anteriores: su única herramienta devuelve rutas, no contenido. Toda la continuidad pasa por una story bible en SQLite que sabe qué capítulo usa cada dato, y por eso un cambio del lector reescribe solo esos capítulos.
