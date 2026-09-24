# Traspaso a la nueva sesión de construcción (VS Code)

Escrito por la sesión coordinadora ("Novaforge continuación con repositorios",
app de escritorio) el 2026-09-24 a las 15:20 UTC, a instrucción del dueño. La
sesión `novaforge-05` se cierra: el dueño abre otra cuenta para ahorrar tokens.
**Lee esto entero antes de tocar nada.** Luego lee `CLAUDE.md`, `AGENTS.md`,
`docs/spec.md` §8 y la sección "ORDEN PARA HOY" al final de `from-design.md`.

## 1. Quién es quién

- **Dueño: David.** Todo va bajo su mando. Una aprobación vale solo si él la
  escribe, y se copia con sus palabras en la cabecera del spec. Una respuesta
  corta o ambigua ("pues a ver") **no** aprueba gastar.
- **Tú (VS Code) = generación y ejecución**: código, tests, runs reales, evals,
  el PDF.
- **La sesión coordinadora = el cerebro**: specs, planes, revisión, `/docs`,
  deck y coordinación. Te escribe por SendMessage si tu sesión aparece en
  `ListAgents`; si no, por este directorio.
- **La sesión de documentación (claude.ai)** deja órdenes del dueño en
  `from-design.md`. Tú contestas en `from-build.md`.

## 2. Plazos

**Entrega: viernes 2026-09-25 por la mañana.** David presenta temprano y el
jueves hay que terminar todo lo obligatorio. **Los opcionales del examen**
(servidor MCP, linters, login, agente de seguridad, etc.) **no se tocan hasta
terminar lo obligatorio.**

## 3. Estado real a las 15:20 UTC

- **No hay ningún orquestador ni servidor vivo.** La máquina se reinició sobre
  las 15:09 UTC.
- **El run del conductor `leo-and-bruno-cross-the-hill` (db2fed5bd97a) está
  muerto desde ayer a las 21:31.** Tiene hechos world, cast (ingestado a mano:
  33 hechos, 6 personajes, 14 filas de cronología) y `outline.md`. La unidad
  outline-write se paró en 100.597 tokens, pero el archivo quedó escrito. **No
  tiene** outline-audit ni ningún capítulo. Cada proceso arranca ya con unos
  48.800 tokens de suelo, así que es casi seguro que los capítulos también
  pasen de 100k.
- **Hay trabajo sin commitear de `novaforge-05` en el checkout**, el enlace
  brief→run:
  - `backend/brief/domain.py`
  - `backend/commons/db/repository.py`
  - `backend/runs/{models,router,service}.py`
  - `migrations/017_run_from_brief.sql`
  - `tests/test_brief_to_run.py`

  **La suite pasa con él: 724 passed, 4 skipped** (replay, a las 15:15 UTC).
  Revísalo y **commitéalo tú primero**, con un mensaje que diga que es trabajo
  de `novaforge-05`. `git pull` no funciona hasta entonces.
- **No commitear** estos archivos de previsualización local:
  - `frontend/vite.preview.config.ts`
  - `output/*/bible/.ingest.json`

  Sí conviene commitear `output/leo-and-bruno-cross-the-hill/outline.md` como
  evidencia.
- En `origin/main` hay cosas nuevas de la sesión de documentación: `a514b44` y
  `b0c9d48` (`docs/browser-mcp.md`, `presentacion/guion.md` y
  `presentacion/README.md`).

## 4. Qué hacer, en este orden

1. **Commitear el trabajo pendiente y hacer `git pull --rebase`.**
2. **Lanzar YA la novela de ejemplo por el camino antiguo**: un solo
   orquestador, perfil `exam` con techo de 60 USD (ya en
   `config/profiles/exam.json`) y el brief 01, que ahora entra por
   `POST /api/runs {brief_id}`.
   - El conductor muerto no puede cerrar 10 capítulos antes de las 18:00 UTC,
     que es la hora límite que David aprobó ("va", spec §8). `from-design.md`
     §2 dice que no hay que esperar a esa hora.
   - Antes de lanzar, **comprueba que no quede otro orquestador vivo**
     (red-team, caso 9).
   - Si salta el techo, se publica con los capítulos promovidos y se declara.
3. **Mientras corre**, lanzar las evals de 3 capítulos (perfil `eval`) sobre
   los briefs **01, 04 y 05**; el 02 solo si sobra presupuesto. Cada validador
   escribe su fila en `validations`, y `evals/results.md` sale de ahí. Si no
   se ejecuta, se escribe "not run: \<motivo\>"; nunca un cero.
4. **Brief 05**: el schema tiene que aceptar `recipient.birth_date` y las
   fechas de los recuerdos, que van a la cronología en el ingest. FLOW-0
   comprueba la coherencia temporal. Sin elan/Lean, `lean_chronology` escribe
   "not run: elan unavailable".
5. **Con la novela terminada:**
   - el PDF v1 → `ejemplos/novela-ejemplo.pdf`;
   - un cambio del lector → v2 con la página de novedades (criterio 5b);
   - la exportación real a Langfuse. Las credenciales solo salen del entorno:
     comprueba que existen y **nunca imprimas sus valores**;
   - la sesión de navegador de `docs/browser-mcp.md`;
   - rellenar las `PENDIENTE` de `presentacion/guion.md`.
6. **Al cerrar cada bloque**, actualizar `from-build.md` con coste, minutos y
   commit, que es por donde David sigue el avance.
7. **Pendiente de declarar** en `docs/verification.md` §3: una unidad que se
   aborta no deja coste en el libro de cuentas. `3aa0c43` ya lo cubre en el
   techo con el máximo entre lo reportado y lo estimado.

## 5. Reglas que no se rompen

- Estos valores no cambian sin un spec aprobado que los nombre (`AGENTS.md`
  §6): el umbral 8, las seis características, los 3 intentos, la línea
  `tools:` de cada agente, patch-then-halt, el techo de 100.000 tokens y el
  techo de presupuesto.
- **Los 100k son por paso** (por turno del orquestador y por paquete de
  agente), no por novela. Si un paso se pasa, se para y se avisa a David.
- **Los agentes van en Haiku; el orquestador va en el modelo de sesión.** Con
  Haiku de orquestador se dejaron de usar los agentes del proyecto.
- SPEC → PLAN → código, con TDD y los tests vistos en rojo primero.
- Cada cifra lleva su procedencia: measured, reported, reconstructed,
  estimated o absent. **Absent nunca es cero.**
- **Privacidad (RGPD).** No reproducir datos personales reales en docs ni en
  mensajes; usar marcadores como [NOMBRE_ANONIMIZADO] o [EMAIL_ELIMINADO].
  Nunca meter secretos en archivos ni en argv.
- **Commits:**
  - solo los archivos propios;
  - `git pull --rebase` antes de empujar;
  - autor David Calderon;
  - el mensaje termina con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Modo economía de tokens**: mensajes cortos y sin repetir lo que ya está en
  el repo.

## 6. Dónde está cada cosa

- El spec del examen y todas las decisiones: `docs/spec.md` (§8).
- Los planes: `specs/PLAN-001-exam.md` y `specs/SPEC-EXAM-003` (el conductor).
- El frontend (Entrevista, Leer, Pedir cambio; 93 tests): `specs/SPEC-EXAM-002`.
- El razonamiento y los hallazgos:
  - `docs/iterations.md`
  - `docs/red-team-log.md`
  - `docs/trade-offs.md`
- TLA+: `tla/` (TLC pasa con 18.253 estados).
- El JDK: `C:\Users\student\tools\jdk-21.0.12.1+1`.
- El deck (Qaracter, 12 slides) es un Artifact de la sesión coordinadora. Las
  cifras que midas van a `from-build.md` y ella las pasa al deck.
