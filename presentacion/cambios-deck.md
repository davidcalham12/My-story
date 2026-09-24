# Cambios pendientes en el deck (`deck-qaracter.pdf`)

Escrito por la sesión coordinadora el 2026-09-24 a las 21:05 UTC, a petición
del dueño: el deck se queda como está y él aplica estos cambios el 25 con la
sesión de diseño. **No cambia el diseño**: misma letra (DM Sans), mismos colores
y mismas plantillas. Solo cambian el texto y las cifras.

Cada cifra lleva su procedencia. Lo que aún no está medido va como
`[pendiente]`; se rellena con lo que `docs/handoff/from-build.md` diga al
terminar cada bloque.

Hay un borrador de referencia con estos cambios ya aplicados, en el mismo
estilo: https://claude.ai/artifact/SvJiJDgognrcPRnxTywkHK (privado, solo del
dueño). Es una guía, no la versión final.

## 1. Cifras que están mal hoy

| diapositiva | dice | debe decir | fuente |
|---|---|---|---|
| 9 · Formal y observabilidad | Langfuse: "1 traza, 12 spans, 100 scores y 12 prompts" | "2 trazas (v1 y v2), 50 llamadas de agente con entrada, salida y caché por separado, 125 scores" | Langfuse `v2/observations` y `v3/scores`, comprobado el 24-09 a las 20:55 UTC tras la reexportación con `--replace` |
| 7 · Validación | TLA+: "en desarrollo (TLC)" | "TLC: 18.253 estados sin errores; TwoServers encuentra el caso 13 y verifica el arreglo". Así no contradice la 9 | `tla/`, commit 8f7513f |
| 6 · Roles y bucle (pie) | "Claude Code orquesta" | "Claude Code orquesta (Sonnet); los agentes corren en Haiku" | e5e3e9b; el stream de la v3 dice `claude-sonnet-5` |
| 6 · Roles y bucle (título) | "Doce agentes" | trece ficheros en `.claude/agents/` (con `bible-critic`, que solo se activa por perfil). Decir "trece" o quitar el número | `.claude/agents/` |
| 11 · Presupuesto (nota) | "Palanca ya construida: orquestador en Sonnet y tres críticos en uno" | "Palancas: orquestador en Sonnet (aplicado el 24-09; la novela de ejemplo corrió en Opus) y bucle del capítulo en código (SPEC-EXAM-006, aprobado)" | e5e3e9b, SPEC-EXAM-006 |
| 2 · Resumen, "Coste bajo control" | "el siguiente paso reduce a la mitad las llamadas por capítulo" | "los agentes son el 8 % del coste (medido); el 92 % es el orquestador, y el siguiente paso aprobado lo sustituye por código" | ver §2 |

## 2. Diapositiva nueva: "Dónde se va el dinero" (tras la 10)

Es el argumento más fuerte del deck.

- **74,20 $ medidos** por la novela de 10 capítulos, en **169 min** y 468 turnos.
- **Medido por modelo** (`modelUsage` del `result` de cada proceso):
  - primer tramo 53,17 $ = Opus 48,79 $ + Haiku 4,38 $;
  - reanudación 21,03 $ = Opus 19,34 $ + Haiku 1,69 $.
- **Resultado: agentes (Haiku) 6,07 $, el 8 %; orquestador (Opus) 68,13 $,
  el 92 %.** Todo medido.
- La estimación por llamada de Langfuse (2,88 $ en 50 llamadas) **se queda
  corta a la mitad**: no ve todas las llamadas ni todo lo que cada una cachea.
  No usarla en el deck; usar la cifra medida. (Corregido el 24-09 a las
  21:25 UTC; la versión anterior de esta nota decía "4 %, estimado".)
- Tabla medida (`modelUsage` del evento `result`):

| tramo | total | orquestador | agentes | min |
|---|---|---|---|---|
| reanudación: capítulos 9–10, estilo y sinopsis | 21,03 $ | 19,34 $ · Opus | 1,69 $ | 51 |
| cambio del lector, capítulo 3 (cortado por el límite de gasto) | 7,52 $ | 6,64 $ · Opus | 0,88 $ | 26 |
| cambio del lector v3, con Sonnet | [pendiente] | [pendiente] | [pendiente] | [pendiente] |

- Langfuse: la novela suma 488.039 tokens de salida; el coste de los agentes
  es 0,44 $ de entrada y caché y 2,44 $ de salida.

## 3. Diapositiva nueva: "Siguiente paso, ya aprobado" (antes de la demo)

- **Título:** "El código conduce; el modelo solo juzga" (SPEC-EXAM-006).
- **Contenido:**
  - Hoy, un orquestador de IA relee el procedimiento en cada turno para
    decidir lo que ya es una regla.
  - Con el bucle en Python, el código ejecuta escritor → cuatro críticos en
    paralelo → nota mínima → reintento, y los agentes siguen en Haiku.
  - Umbral 8, seis características y tres intentos: sin cambios.
- **Más estricto:** coste por agente medido; el techo de 100k se comprueba
  antes de cada llamada.
- **Descartado:** Haiku como orquestador (run `phantom-station`: dejó de usar
  los agentes y el escritor perdió su aislamiento).
- **Prueba:** 1 capítulo con techo de 3 USD, [coste y minutos pendientes],
  frente a los 7,52 $ y 26 min del capítulo orquestado.

## 4. Demo y cierre (diapositiva 12)

- **La demo:** "El perro se llama Nala" no es lo que se ejecutó. El cambio
  real es **"el observatorio de cartón pasa a ser una casa del árbol"**
  (hecho 36; capítulos 3 y 10) → v3 con su página de novedades. Cambiar el
  ejemplo también en la diapositiva 4. [coste y minutos de la v3: pendiente]
- **Siguientes pasos:** hoy dice "servidor MCP, login y análisis de seguridad".
  El MCP (solo lectura) y la revisión de seguridad **ya están hechos**
  (SPEC-EXAM-005, O2 y O3). Pasarlos a un bloque "Hecho además", junto con el
  linter de prosa (O1) y TLA+ TwoServers (O4). Siguientes pasos que quedan:
  - el bucle del capítulo en código;
  - continuar o mandar a la papelera, desde la web, una novela parada
    (SPEC-EXAM-007, aprobado);
  - login.
- **Diapositiva 9, última frase:** añadir un tercer fallo que delató el
  registro: el orquestador corría en Opus cuando la configuración decía Sonnet.

## 5. Si da tiempo

Si antes de la presentación se mide la novela `tiny` que el dueño lance desde
la web, sus cifras (coste, minutos, capítulos a la primera) van en la
diapositiva de coste como segundo dato medido de una novela entera, ya con
Sonnet.
