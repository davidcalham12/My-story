# from-build — buzón de la sesión constructora → sesión de diseño

Actualizado: 2026-09-23, sesión `novaforge-05` (máquina virtual, VS Code). Los
detalles están en los ficheros que se citan; esto no los repite.

## 1. Estado del repo

- Rama viva `backend-v1`, sin fusionar a `main` (decisión del profesor).
- Runbook backend v1 completo (Pasos 0–12): `docs/REPORT-backend-v1.md`.
  SPEC-007 y PLAN-007 aprobados por dictado del dueño (la cabecera lo dice).
  SPEC-008/PLAN-008 (import en BD vacía, archivo conoce `prose_check.json`).
- **509 tests backend, 19 frontend**, `tsc` limpio, self-tests de Node en verde.
- Dos runs reales por el backend el 22 (`tiny` $16,25, `stress` $20,15, ambos
  conformes): `domain-knowledge.md` §8. Un tercer run (`salvage-crew-…`, 23 a
  las 02:20Z, lanzado desde el panel) murió con los servidores a las 02:45Z; su
  fila queda `FLOW-4` hasta que el barrido de arranque la marque
  `halted: process`; su `output/` está sin trackear a la espera del dueño.
- `verification.md` v3: 23 garantías, §3 con 21 huecos (3.19–3.21 nuevos), §9.

## 2. Lo que llegó hoy y dónde se colocó

- `specs/SPEC-009-frontend-v2.md` — **draft**, tal cual la escribió diseño.
  Aprobación pendiente de grill (lo hace la sesión "Novaforge continuación con
  repositorios") e incorporación; luego cabecera.
- `docs/handoff/from-design.md` — tal cual.
- `docs/brief/` — brief, anexos B/C/D, runbook, plan de examen (README ahí).
- `AGENTS.md` §1 — regla del buzón.
- Skills: las cinco de `my-factory` instaladas en la VM (texto puro, leídas);
  las siete que la VM tenía y el seed no, subidas a `my-factory` (`b654582`).

## 3. Respuestas a `from-design.md`

- §2 prueba 1 (`--max-budget-usd` a $1) y prueba 2 (tokens en el stream): no
  hechas todavía; son de la sesión constructora de código, tras SPEC-009.
- §3 `OBS` de SPEC-001-commons ("real Anthropic client behind a flag"):
  confirmado como incoherencia; pendiente de nota con `coherencia-docs`.
- §4 plan de 48 h: los 12 endpoints y el frontend P0 los toma la otra sesión
  de la VM en cuanto SPEC-009 esté aprobada.

## 4. Reparto vigente entre las dos sesiones de la VM

`novaforge-05`: docs, specs, informe, GitHub, skills, `my-factory`, buzón.
"Novaforge continuación con repositorios": código bajo `backend-v1` (endpoints,
frontend P0, pruebas de $1). Un committer a la vez; `git pull` antes de tocar;
aviso antes de commitear.
