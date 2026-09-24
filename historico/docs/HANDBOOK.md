> ⚠️ **Aviso (2026-09-23, 20:30 UTC).** El repositorio del examen que tiene el
> código, la spec aprobada (`SPEC-EXAM-001`), el plan por horas (`PLAN-001-exam`)
> y los cinco briefs es **https://github.com/davidcalham12/StoryMaker**, clonado
> de `novaforge-v2` @ `055c31d` con historia. Este repo (`My-story`) conserva el
> esqueleto del 15-09 y los documentos de la sesión de diseño (`docs/HANDBOOK.md`,
> `docs/EXAM-PLAN.md`, `docs/EXAM-RUNBOOK.md`) como referencia. **Pendiente de
> que el dueño confirme cuál es la entrega.** Decisiones del dueño ya tomadas:
> entrega **viernes 2026-09-25 por la mañana**; empresa presentadora **Qaracter**
> (identidad del sistema de diseño de la organización); lectura en **PDF**, no
> web; novelas en Haiku.

# Handbook — qué se hizo, qué fue lo último, cómo seguir

Para la sesión de Claude Code (o la persona) que retome este repositorio sin
historial. Fecha: 2026-09-23. Sin secretos ni datos personales.

## 1. Quién es quién

| sesión | dónde | hace |
|---|---|---|
| **Diseño** | portátil del dueño (tiene `git`, sin acceso a la VM) | piensa, especifica, revisa; comitea sólo docs y specs en `draft` |
| **`novaforge-05`** | máquina virtual, VS Code | docs, specs, informes, GitHub, skills, `my-factory`, buzón |
| **"Novaforge continuación con repositorios"** | máquina virtual | código bajo `backend-v1`, runs reales |
| **el dueño** | — | aprueba specs y planes **editando la cabecera del fichero**; decide modelos, nombres, fechas |

Las sesiones **no pueden hablarse** (Remote Control bloqueado por la
organización). Se comunican por el repositorio: `docs/handoff/from-design.md`
y `docs/handoff/from-build.md`, en `novaforge-v2` y aquí. Regla: al empezar,
leer `docs/handoff/`; al cerrar un bloque, actualizar tu fichero. Un committer
a la vez; `git pull --rebase` antes de tocar.

## 2. Qué existe ya (en `novaforge-v2`, rama `backend-v1`)

Un harness que escribe novelas con contexto acotado, **funcionando de punta a
punta**: Claude Code orquesta (`claude -p`, sin API key), FastAPI lanza y
observa, SQLite archiva. Diez agentes, gate de **seis** características ≥ 8 con
tres oportunidades y `patch_then_halt`, hoja de retroalimentación validada,
**524 tests a $0**, once novelas medidas, coste real por run desde el evento
`result`. `docs/verification.md` con 23 garantías letradas (T/A/I/D/U) y los
huecos declarados. Proceso `AGENTS.md`: docs → spec aprobada → plan aprobado →
código con TDD.

Lo que falta allí: **el frontend** (SPEC-009 aprobada; `PLAN-009` sin escribir;
4 páginas de 6; sin diseño), Langfuse con scores, y todo lo del examen.

## 3. Lo último que pasó (23-09, tarde)

- PLAN-010 ejecutado: el vigilante de contexto ya mide tokens reales por
  subagente (la cifra estaba en el stream bajo otra clave).
- **Los diez agentes pasaron a Haiku** (SPEC-011) para ahorrar cuota. Todo lo
  medido antes fue con Opus/Sonnet y no es comparable. Propuesto un perfil
  `final` con los modelos originales para la novela de ejemplo del examen.
- **`--max-budget-usd` frena de verdad**: probado con techo $1 → la CLI paró en
  6,6 s. Y el primer turno del orquestador cuesta ~$1 antes de despachar a nadie.
- El dueño agotó la cuota una vez. Política: Fable para razonar; **Sonnet 5 para
  vigilar y para lo mecánico**; Haiku en runs de prueba.

## 4. Qué decide el examen

*"Un proyecto sin evals con resultados medibles, o sin documentación de proceso
en `/docs`, no aprueba."* Evidencias obligatorias: la tabla de evals con
números; el coste real por novela desde Langfuse; la demo de un cambio del
lector propagado a los capítulos afectados; `ejemplos/novela-ejemplo.pdf`.
Lean y TLA+ se construyen **después** sobre un sistema que ya funciona.
Detalle: `docs/EXAM-PLAN.md`; orden: `docs/EXAM-RUNBOOK.md`.

## 5. Pendiente del dueño (sin esto hay pasos que no arrancan)

1. **Nombre de la identidad visual** (panel + presentación). Bloquea `DESIGN.md`.
2. **Fecha de entrega del examen.** Sin ella el runbook está por niveles, no por días.
3. Web + PDF exportado (recomendado) o sólo PDF.
4. Si en la VM se pueden instalar **Java** (TLC) y **elan/lake** (Lean).
5. Aprobar por escrito lo que vaya llegando en `draft`.

## 6. Lo que no hay que hacer

Pedir o pegar claves (se leen del entorno). Pasar la tarea a `claude -p` por
argv (stdin, sin shell). Dar al escritor acceso a prosa previa. Inventar
números (`absent` no es cero). Tocar el 8, las seis características, el tercer
intento, la línea `tools:` de un agente o los techos sin spec aprobada. Código
sin plan aprobado. Rangos sin criterio en prompts. Creer al agente sobre su
propio trabajo. Escribir en PowerShell sin cuidar el BOM.
