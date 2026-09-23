# Runbook — backend v1: de la spec a la rama probada

Pasos estructurados, en orden, para ejecutar la tarea de la profesora:

> Terminar de definir el documento de verificación (formas de verificar y
> posibles modos de fallo). Definir una spec con todo lo necesario para generar
> un backend funcional. Crear una rama nueva (copia de la actual) donde se
> ejecutará la spec y se pondrá a prueba.

Cada paso dice **quién** lo hace (tú, o la sesión constructora), **qué entra**,
**qué sale** y **cuándo está hecho**. No se salta ningún paso: las puertas de
aprobación son el proceso de `agents.md`.

Máquina: la de la copia actual (`C:\Users\student\Desktop\novaforge`).
Fecha: 2026-09-22.

---

## Paso 0 — Comprobar que todo lo previo está en su sitio

**Quién:** tú, con la sesión constructora.

**Entra:** el brief (`NOVAFORGE-V2-BRIEF.md`) y sus anexos B, C, D.

**Qué hacer:** pídele a la sesión que confirme, con rutas:

1. Las diez skills instaladas en `~/.claude/skills/` (Anexo §2.1). Especialmente
   `grilling`, `fastapi`, `sqlite`, `sqlite-vec`, `sentence-transformers`,
   `verification`.
2. `docs/definitions.md`, `docs/domain-knowledge.md`, `docs/architecture.md`
   existen y `architecture.md` tiene las tres secciones del Anexo B §3
   (orquestación, memoria en cuatro capas, 100k concurrentes).
3. `agents.md` describe el proceso spec → plan → código (Anexo B §4), y **no**
   es el catálogo de agentes.
4. `claude.md` empieza con "Read `agents.md` first".
5. No hay ninguna referencia a `ANTHROPIC_API_KEY` ni al SDK de Anthropic
   (Anexo C).

**Hecho cuando:** la sesión responde con las rutas y tú ves los cinco puntos.
Si falta algo, se hace antes de seguir; **este runbook no lo repite**.

Prompt:

> Confirma con rutas exactas: (1) qué skills hay en `~/.claude/skills/`; (2)
> que `docs/architecture.md` tiene las secciones de orquestación, memoria en
> cuatro capas y 100k concurrentes; (3) que `agents.md` describe el proceso
> spec → plan → código; (4) que `claude.md` remite a `agents.md`; (5) que
> `grep -ri anthropic_api_key` y `grep -ri "import anthropic"` no devuelven
> nada fuera de `docs/`. Si algo falta, dilo y no sigas.

---

## Paso 1 — Colocar los dos documentos nuevos

**Quién:** tú.

**Entra:** `docs/verification.md` (v1) y `specs/SPEC-001-backend-v1.md`.

**Qué hacer:** copiarlos a la máquina `student` en esas mismas rutas. Si la
sesión ya había generado un `verification.md` con la skill, **no lo borres**:
guárdalo como `docs/verification.generated.md` para el paso siguiente.

**Hecho cuando:** los dos ficheros están en el repo, en la rama actual
(`claude-orchestrator`), sin commit todavía.

---

## Paso 2 — Consolidar `verification.md`

**Quién:** la sesión constructora.

**Entra:** `docs/verification.md` (v1) y, si existe, `verification.generated.md`.

**Qué hacer:** fusionar en uno. Se queda la **unión** de garantías, huecos y
modos de fallo; ante duplicados, se queda la letra **más baja que sea cierta**,
nunca la más alta. Después, revisar cada garantía crítica: si tiene letra I o D
y no está en la tabla de huecos, añadirla.

**Después de fusionar, pasar `coherencia-docs`.** Antes, crear
`docs/_authority.md` con nuestra tabla, para que la skill la use en vez de la
suya:

```markdown
# Authority
| statement type | wins | others |
|---|---|---|
| what a term means | docs/definitions.md | use it, never redefine |
| how the domain works | docs/domain-knowledge.md | apply it |
| technical decisions, agents, process, limits | docs/architecture.md | reference it |
| operating rules for the coding agent | agents.md | invoke them |
| Claude Code specifics (commands, permissions) | claude.md | derived from agents.md |
| verification method and T/A/I/D/U letter per guarantee | docs/verification.md | derived: loses to architecture.md on facts |
| requirements of one deliverable | specs/SPEC-*.md | derived from architecture.md |
| implementation order | specs/PLAN-*.md | derived from its SPEC |
```

Luego la skill, en modo informe. Se resuelve el **Lote A** (automáticas) con
una aprobación tuya; el **Lote B** (decisiones) pregunta por pregunta. Lo que
salga como `CND` (una garantía que era cierta *porque* algo no existía, y ya
existe) va primero y lo miras tú.

**Hecho cuando:** existe un solo `docs/verification.md` con las ocho secciones
(letras, garantías, código antes que agente, huecos, validadores, modos de
fallo, mapa del catálogo, historial), `verification.generated.md` se ha
borrado, `docs/_authority.md` existe, y el informe de `coherencia-docs` no
tiene incidencias de severidad alta abiertas.

Prompt adicional:

> Crea `docs/_authority.md` con la tabla que te paso. Después usa la skill
> `coherencia-docs` sobre `docs/` y `claude.md`, sólo en modo informe.
> Detente en el informe y muéstramelo.

Prompt:

> Fusiona `docs/verification.md` con `docs/verification.generated.md` si
> existe. Regla: unión de filas; en duplicados, la letra más baja que sea
> cierta. Comprueba que toda garantía crítica con letra I o D tiene fila en
> "huecos conocidos". Borra el generado al terminar. Dime qué filas añadiste y
> cuáles cambiaron de letra.

---

## Paso 3 — Crear la rama

**Quién:** tú (o la sesión, si prefieres).

**Qué hacer:**

```bash
git checkout claude-orchestrator
git pull
git add docs/verification.md specs/SPEC-001-backend-v1.md
git commit -m "verification v1 and SPEC-001 backend v1 (draft)"
git checkout -b backend-v1
```

Los documentos se comitean **en la rama actual** antes de cortar la nueva, para
que `claude-orchestrator` conserve la spec aunque la rama de trabajo se descarte.

**Hecho cuando:** `git branch --show-current` devuelve `backend-v1` y
`git log -1` muestra el commit de los documentos.

---

## Paso 4 — Preguntas antes de aprobar (grill sobre la spec)

**Quién:** la sesión pregunta; tú respondes.

**Entra:** `specs/SPEC-001-backend-v1.md` y `docs/`.

**Qué hacer:** la sesión lee la spec y `docs/` y usa `grilling` para hacer sólo
las preguntas que **no puede resolver leyendo el repo**. Tú contestas. Las
respuestas se incorporan a la spec por la sesión (no a la conversación).

**Hecho cuando:** la sesión dice que no le quedan preguntas abiertas, y la spec
refleja tus respuestas.

Prompt:

> Lee `docs/` completo y `specs/SPEC-001-backend-v1.md`. Con la skill
> `grilling`, hazme sólo las preguntas que no puedas resolver leyendo el repo,
> en rondas, con tu respuesta recomendada en cada una. Cuando yo conteste,
> incorpora las respuestas a la spec en la sección que corresponda. No escribas
> nada más hasta que te diga que está aprobada.

---

## Paso 5 — Aprobar la spec

**Quién:** tú, a mano.

**Qué hacer:** editar la cabecera de `specs/SPEC-001-backend-v1.md`:

```yaml
status: approved
approved_by: <tu nombre>
approved_on: 2026-09-XX
```

y comitear:

```bash
git add specs/SPEC-001-backend-v1.md
git commit -m "SPEC-001 approved"
```

**Por qué a mano:** `agents.md` dice que un "ok" en el chat no aprueba nada; el
fichero sí. Es la primera puerta.

**Hecho cuando:** el commit existe. La sesión no puede pasar al paso 6 sin él.

---

## Paso 6 — Escribir el plan de implementación

**Quién:** la sesión constructora.

**Entra:** SPEC-001 aprobada, `docs/architecture.md`, `docs/verification.md`.

**Qué hacer:** escribir `specs/PLAN-001-backend-v1.md`, estado `draft`, con
esta estructura obligatoria:

1. **Referencia:** `SPEC-001`, hash del commit aprobado.
2. **Orden de construcción**, en fases, cada una con sus tests **antes** que su
   código:
   - 6.1 `backend/tests/fake_claude/` — el `claude` falso que reproduce un
     stream grabado, con interruptores (línea malformada, sin `result`, exceso
     de coste, cinco críticos > 100k, crítica de forma desconocida). Grabar el
     stream desde el run `the-beginning-after-the-end` o desde un run `tiny`
     nuevo.
   - 6.2 `commons/db` — esquema (§5 de la spec), migraciones, WAL, un escritor.
   - 6.3 `commons/config` — carga de `flow.yaml` + config + perfiles;
     `config_hash`; **validador `SKILL.md` ↔ `flow.yaml`**; **validador de front
     matter de agentes** (AC-8, AC-9).
   - 6.4 `commons/runner` — spawn sin shell, stdin, parser línea a línea,
     persistencia de eventos, derivación de estado, `cost.json`.
   - 6.5 `commons/budget` — vigilante de coste y de contexto (AC-5, AC-6).
   - 6.6 `commons/log` — filas de `calls` desde `usage`.
   - 6.7 `runs` — endpoints, SSE con `Last-Event-ID`, `halt`, importador de las
     ocho novelas (AC-7), marcado de huérfanos al arrancar.
   - 6.8 `commons/search` — embeddings locales, `vec0`, CLI, degradación
     (AC-11).
   - 6.9 instrumentos — `outline_audit` (AC-12), `validate_sheet` (AC-13),
     `measure` (AC-14); los `.mjs` quedan hasta que los self-tests coincidan.
   - 6.10 endpoints de lectura por feature con normalización de rutas (AC-10)
     y `source` en cada número.
   - 6.11 `/health`.
   - 6.12 **cambios en `SKILL.md`** (§8 de la spec): borradores rechazados,
     `date -u`, llamadas a los tres instrumentos, estimación del paquete,
     hechos estructurados. Cada uno con el test o la comprobación que lo cubre.
3. **Tests por fase**, nombrados, con el criterio de aceptación que cubren.
4. **Actualizaciones de docs** por fase: qué cambia en `architecture.md`,
   `verification.md` (huecos que se abren o cierran), `domain-knowledge.md`.
5. **Huecos que el plan deja**, con nivel.
6. **Estimación de esfuerzo** por fase, en horas de sesión, marcada `estimated`.

**Hecho cuando:** el fichero existe con las seis partes y estado `draft`.

Prompt:

> SPEC-001 está aprobada. Escribe `specs/PLAN-001-backend-v1.md` en estado
> `draft` con esta estructura: referencia a la spec y su commit; orden de
> construcción en fases con los tests antes que el código en cada una,
> empezando por el `claude` falso y `commons` y terminando por los cambios a
> `SKILL.md` de la spec §8; tests nombrados por fase con el criterio de
> aceptación que cubren; actualizaciones de docs por fase; huecos que deja; y
> estimación por fase marcada como estimada. No escribas código.

---

## Paso 7 — Bucle plan ↔ arquitectura hasta hueco cero

**Quién:** la sesión constructora; tú lees el informe de cada vuelta.

**Entra:** `PLAN-001` (draft), `docs/architecture.md`, `SPEC-001`,
`docs/verification.md`.

**Qué hacer:** iterar. En cada vuelta la sesión compara el plan con la
arquitectura y la spec, lista los huecos con precisión (qué requisito o decisión
no tiene paso en el plan, o qué paso del plan no responde a nada), corrige el
plan, y repite.

**Criterio de parada — dos condiciones, se para en la primera que se cumpla:**

1. **Hueco cero:** una vuelta completa sin ningún hueco nuevo en ninguna
   dirección (todo requisito de la spec y toda decisión de la arquitectura
   tienen paso; todo paso responde a algo).
2. **Cinco vueltas.** Si a la quinta sigue habiendo huecos, se para y **los
   huecos restantes se escriben en el plan como huecos declarados**, no se
   siguen dando vueltas. Un bucle que no converge en cinco está señalando un
   problema en la spec o en la arquitectura, no en el plan.

**Al cerrar el bucle, una pasada de `coherencia-docs`** sobre `docs/`,
`claude.md`, la spec y el plan. El bucle detecta huecos plan ↔ arquitectura;
la skill detecta lo que el bucle no mira: referencias `§N` rotas, el mismo
número con dos valores en dos documentos, términos que derivaron. Sólo Lote A
automático; el resto, informe.

**Hecho cuando:** el plan tiene una sección "Bucle de convergencia" con el
número de vueltas, qué cambió en cada una, y los huecos que quedaron
declarados (si los hay); y el informe de `coherencia-docs` no tiene `REF` ni
`FAC` abiertas entre el plan, la spec y la arquitectura.

Prompt:

> Haz un bucle de mejora sobre `specs/PLAN-001-backend-v1.md`: en cada vuelta
> compáralo con `docs/architecture.md`, `specs/SPEC-001-backend-v1.md` y
> `docs/verification.md`; lista cada hueco en ambas direcciones; corrige el
> plan; repite. Para cuando una vuelta completa no encuentre ningún hueco, o a
> la quinta vuelta — en ese caso deja los huecos restantes escritos en el plan
> como declarados. Añade al plan una sección "Bucle de convergencia" con
> cuántas vueltas hubo y qué cambió en cada una.

---

## Paso 8 — Aprobar el plan

**Quién:** tú, a mano.

**Qué hacer:** leer el plan, especialmente el orden de fases y los huecos
declarados. Si estás de acuerdo:

```yaml
status: approved
approved_by: <tu nombre>
approved_on: 2026-09-XX
```

```bash
git add specs/PLAN-001-backend-v1.md
git commit -m "PLAN-001 approved"
```

**Hecho cuando:** el commit existe. Segunda puerta. Sin ella no hay código.

---

## Paso 9 — Ejecutar el plan con TDD

**Quién:** la sesión constructora, fase a fase.

**Entra:** `PLAN-001` aprobado, en la rama `backend-v1`.

**Qué hacer:** para cada fase del plan, en orden:

1. Escribir los tests de la fase. **Ejecutarlos y verlos fallar.** Si un test
   pasa antes de escribir el código, el test no prueba nada: se arregla el test.
2. Escribir el código mínimo que los pasa.
3. Refactorizar con los tests en verde.
4. Actualizar los docs que el plan asigna a esa fase.
5. Un commit por fase, con el nombre de la fase, y **el resultado de los tests
   en el mensaje** (cuántos, cuántos pasan).
6. Si algo difiere de la spec, **la spec se actualiza en el mismo commit** con
   una nota de por qué.

**Regla de parada dentro del paso:** si una fase lleva **tres commits** sin
llegar a tests en verde, la sesión se detiene y reporta qué está bloqueado, en
vez de seguir intentando. Esa es la señal de que el plan o la spec tienen un
error.

**Hecho cuando:** todas las fases del plan tienen su commit con tests en verde,
y el CI (GitHub Actions con el `claude` falso) pasa en la rama.

Prompt (uno por fase, o uno global si prefieres):

> Ejecuta la fase <N> de `PLAN-001` en la rama `backend-v1` con TDD estricto:
> escribe los tests, ejecútalos y muéstrame que fallan; luego el código mínimo;
> luego refactor. Un commit con el resultado de los tests en el mensaje. Si
> algo difiere de la spec, actualiza la spec en el mismo commit y dime qué. Si
> tras tres commits no estás en verde, para y dime qué bloquea.

---

## Paso 10 — Poner a prueba la rama

**Quién:** la sesión ejecuta; tú compruebas.

**Entra:** la rama con todas las fases.

**Qué hacer, en orden:**

1. **Los 17 criterios de aceptación de la spec**, uno a uno. Los `T` se
   ejecutan; los `A` se ejecutan como grep o análisis; los `I` los miras tú; el
   `D` (AC-15) es la novela real.
2. **La novela real:** un run `tiny` desde `POST /runs` hasta `complete`, con
   `cost.json` escrito por el backend. Comparar el coste con los **$7,45** del
   run equivalente actual y explicar la diferencia en `domain-knowledge.md`.
3. **El run de estrés:** perfil `stress` desde el backend. **Debe detenerse por
   la auditoría del guion antes de FLOW-4**, no en el capítulo 3 por
   `patch_then_halt`. Si muere en el capítulo 3, AC-12 no está cumplido de
   verdad.
4. **Importación:** las ocho novelas viejas visibles por `GET /runs` con
   `source = reconstructed`.
5. **Los tres `--self-test`** en verde.

**Hecho cuando:** los 17 criterios tienen resultado escrito (pasa / no pasa /
pendiente con motivo) en una tabla al final de la spec, y el run real existe con
su coste.

Prompt:

> Recorre los 17 criterios de aceptación de SPEC-001 en orden. Ejecuta los T y
> los A y pega la salida; para los I dime qué tengo que mirar y dónde; para el
> D lanza un run `tiny` real por `POST /runs` y espera al `complete`. Después
> lanza el perfil `stress` y dime dónde se detuvo y por qué. Añade al final de
> la spec una tabla con el resultado de cada criterio.

---

## Paso 11 — Cerrar `verification.md` con lo aprendido

**Quién:** la sesión; tú revisas.

**Entra:** los resultados del paso 10.

**Qué hacer:** actualizar `docs/verification.md`:

- Cada garantía cuya letra haya cambiado (por ejemplo, algo que era `I` y ahora
  tiene test) sube; nada baja sin motivo escrito.
- Cada hueco que se cerró se sustituye por la evidencia que lo cerró.
- Cada modo de fallo que **ocurrió** durante los pasos 9 y 10 y no estaba en la
  tabla, se añade. Los que estaban, se marcan con "ocurrió el <fecha>".
- Versión 2 en el historial, con qué cambió.

**Después, `coherencia-docs` otra vez**, y aquí es donde más vale: el código ya
existe, así que las afirmaciones de estado de `verification.md` ("previsto",
"vacío", "por ahora") pueden haber caducado (`EDO`), y las garantías que eran
ciertas porque algo no existía (`CND`) hay que reabrirlas. Ese informe se lee
antes de dar por cerrada la v2.

**Hecho cuando:** `verification.md` es v2, cada cambio respecto a v1 está en el
historial, y el informe de `coherencia-docs` no tiene `CND` ni `EDO` abiertas.

---

## Paso 12 — Informe y entrega

**Quién:** la sesión redacta; tú entregas.

**Qué hacer:** un `docs/REPORT-backend-v1.md` de una página:

- qué se construyó, por fase, con el número de tests;
- los 17 criterios con su resultado;
- el coste del run real frente al estimado, y por qué;
- los huecos que quedan, con su nivel;
- qué cambió en la spec durante la ejecución y por qué;
- lo que **no** se hizo y por qué.

La rama `backend-v1` **no se fusiona a `claude-orchestrator`** hasta que la
profesora lo vea. La spec y `verification.md` ya están en la rama original
desde el paso 3.

**Hecho cuando:** el informe existe y tú lo has leído entero.

---

## Resumen de puertas

| puerta | quién | qué desbloquea |
|---|---|---|
| Paso 0 completo | tú | todo lo demás |
| Spec aprobada (paso 5) | tú, en el fichero | escribir el plan |
| Plan aprobado (paso 8) | tú, en el fichero | escribir código |
| Tests en verde por fase (paso 9) | CI | la fase siguiente |
| 17 criterios con resultado (paso 10) | la sesión + tú | cerrar verification y entregar |

Nada de lo que hay entre puertas se salta. Si una puerta no se puede cruzar, la
respuesta correcta es volver al documento anterior, no forzarla.
