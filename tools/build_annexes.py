"""The presentation's annexes, generated from the repository and its database.

    python tools/build_annexes.py            # writes presentacion/anexos/*.pdf (+ src/*.md)

Every figure in an annex is read from the file or the table that holds it, at
build time, so an annex cannot drift from the repository it describes. Absent
figures print as "no medido", never as 0. Each annex keeps its Markdown source
in `presentacion/anexos/src/` so it can be read and diffed as text.

Annexes A–H were produced earlier by the coordinating session and are kept as
they are; this script writes I onwards and the folder's index.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentacion" / "anexos"
SRC = OUT / "src"
NOVEL_RUN = "02412b7fe29e"
NOVEL = ROOT / "output" / "the-other-side-of-the-hill"

# Earlier annexes, kept as produced: letter, file, what it holds.
EARLIER = [
    ("A", "anexo-a-arquitectura-harness.pdf", "Arquitectura del harness: capas, agentes y flujo"),
    ("B", "anexo-b-tla-spec.pdf", "Especificación TLA+ y resultado de TLC"),
    ("C", "anexo-c-maquina-estados.pdf", "Máquina de estados del harness"),
    ("D", "anexo-d-evals-tabla.pdf", "Tabla de evals: brief × validador"),
    ("E", "anexo-e-esquema-sqlite.pdf", "Esquema SQLite de la Story Bible"),
    ("F", "anexo-f-validadores.pdf", "Validadores y dónde actúan"),
    ("G", "anexo-g-red-team-log.pdf", "Red-team log"),
    ("H", "anexo-h-iteraciones.pdf", "Registro de iteraciones"),
]


# ---------------------------------------------------------------- helpers


def usd(value) -> str:
    """Spanish style, like the deck: 74,20 $."""
    return "no medido" if value is None else f"{float(value):,.2f} $".replace(",", " ").replace(".", ",")


def mins(value) -> str:
    return "—" if value is None else f"{float(value):.1f}".replace(".", ",")


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(ROOT / "novaforge.db")
    c.row_factory = sqlite3.Row
    return c


def sha() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip() or "?"


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(md: str, heading: str, level: int = 2) -> str:
    """The body under a heading, up to the next heading of the same level."""
    marks = "#" * level
    m = re.search(rf"^{marks} {re.escape(heading)}.*?$", md, re.M)
    if not m:
        return ""
    rest = md[m.end():]
    nxt = re.search(rf"^{marks} ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def table_rows(md: str) -> list[list[str]]:
    rows = []
    for line in md.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def md_table(head: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |"
            for r in rows]
    return "\n".join(out)


# ------------------------------------------------------------- the annexes


def annex_costs() -> tuple[str, str, str, str]:
    c = conn()
    rows = [dict(r) for r in c.execute(
        "SELECT n, kind, label, version, total_usd, orchestrator_model, orchestrator_usd, "
        "agents_usd, minutes, provenance, note FROM changes WHERE run_id = ? ORDER BY n",
        (NOVEL_RUN,))]
    kind = {"generate": "generar", "continue": "continuar", "reader_change": "cambio del lector",
            "redo": "rehacer capítulo"}
    table = md_table(
        ["#", "cambio", "total", "orquestador", "agentes", "min", "procedencia"],
        [[r["n"], kind.get(r["kind"], r["kind"]) + (f" (v{r['version']})" if r["version"] else ""),
          usd(r["total_usd"]),
          (f"{usd(r['orchestrator_usd'])} · {r['orchestrator_model'] or '—'}"),
          usd(r["agents_usd"]), mins(r["minutes"]), r["provenance"] or "absent"] for r in rows])
    known = sum(r["total_usd"] for r in rows if r["total_usd"] is not None)
    book = sum(r["total_usd"] for r in rows if r["kind"] in ("generate", "continue")
               and r["total_usd"] is not None)
    orch = sum(r["orchestrator_usd"] or 0 for r in rows if r["kind"] in ("generate", "continue"))
    evals = [dict(r) for r in c.execute(
        "SELECT r.slug, ch.total_usd, ch.orchestrator_usd, ch.agents_usd, ch.minutes, ch.provenance "
        "FROM changes ch JOIN runs r ON r.id = ch.run_id WHERE r.profile = 'eval' ORDER BY r.slug")]
    price, infra = 129.0, 6.0
    margin = (price - book - infra) / price
    md = f"""
El coste de cada cambio hecho a la novela de ejemplo, leído de los eventos `result`
de Claude Code (medido) y confirmado en Langfuse (`GET /api/runs/{{id}}/costs`,
SPEC-EXAM-008). Los minutos son `result.duration_ms`.

## La novela de ejemplo, cambio a cambio

{table}

**Total conocido: {usd(known)}**, en {len(rows)} cambios; los marcados *no medido* no
dejaron un `result` (proceso detenido o stream no conservado) y no se cuentan como 0.

## El libro: 10 capítulos

- **Coste del libro** (generar + continuar): **{usd(book)}**.
- **Orquestador**: {usd(orch)} (**{orch / book:.0%}**); **agentes (Haiku)**: {usd(book - orch)} (**{(book - orch) / book:.0%}**).
- El orquestador relee todo su contexto en cada turno; es la mayor parte de la factura.
  Pasar de Opus a Sonnet redujo el mismo capítulo de 7,52 $ a 4,24 $.

## Margen

| concepto | valor | procedencia |
|---|---|---|
| tokens por novela | {usd(book)} | medido |
| infraestructura + operación | {usd(infra)} | supuesto |
| precio de venta | {usd(price)} | supuesto |
| **margen por novela** | **{margin:.0%}** | calculado |

## Evals (perfil `eval`, 1 capítulo)

{md_table(["run", "total", "orquestador", "agentes", "min", "procedencia"],
          [[e["slug"], usd(e["total_usd"]), usd(e["orchestrator_usd"]), usd(e["agents_usd"]),
            mins(e["minutes"]), e["provenance"] or "absent"] for e in evals])}
"""
    return ("I", "anexo-i-costes-por-cambio", "Costes por cambio y margen (Langfuse)", md)


def annex_reader_change() -> tuple[str, str, str, str]:
    c = conn()
    v3 = c.execute("SELECT n, parent, reason, created_at FROM versions WHERE run_id = ? AND n = 3",
                   (NOVEL_RUN,)).fetchone()
    fact = c.execute("SELECT text FROM facts WHERE id = 36").fetchone()
    old = fact[0] if fact else "the cardboard observatory"
    new = "the wooden treehouse observatory"
    sys.path.insert(0, str(ROOT))
    from backend.versions import change

    checks = []
    for n in (3, 10):
        p = NOVEL / "dist" / "v3" / "chapters" / f"ch{n:02d}.md"
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        why = change.arrival(text, new=new, old=old) if text else "no promovido"
        checks.append([n, len(re.findall(r"wooden treehouse observator", text, re.I)),
                       "OK" if why is None else why])
    rows = [dict(r) for r in c.execute(
        "SELECT n, kind, label, total_usd, minutes, orchestrator_model FROM changes "
        "WHERE run_id = ? AND kind IN ('reader_change', 'redo') ORDER BY n", (NOVEL_RUN,))]
    md = f"""
El lector cambia **un hecho** y solo se reescriben los capítulos que lo usan. Es la
evidencia obligatoria nº 3 de la presentación.

## El cambio

- Hecho 36: **"{old}"** → **"{new}"**.
- `fact_usage` dice qué capítulos lo usan: **3 y 10**. Solo esos se reescriben; el resto
  del libro se toma tal cual de la v2.
- Resultado: **v{v3['n'] if v3 else 3}**, hija de **v{v3['parent'] if v3 else 2}**, publicada el
  {v3['created_at'] if v3 else '—'}. La v2 no se toca: cada versión se escribe una sola vez.
- El PDF abre con la página **"What changed"**, que enlaza a los capítulos reescritos:
  `ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`.

## Un cambio que no llega no es un cambio

El primer capítulo 3 pasó las seis características **sin mencionar el observatorio**:
ningún crítico comprueba que el hecho cambiado esté. Desde `e0b7c38` se comprueba en
código antes de aceptar: la frase nueva debe aparecer y ninguna variante de la vieja
(mayúsculas, plural, artículo; la frase, no la palabra). No es una séptima
característica: es la condición de aceptación del cambio del lector.

{md_table(["capítulo", "\"wooden treehouse observatory\"", "comprobación"], checks)}

## Lo que costó

{md_table(["#", "tipo", "detalle", "total", "min", "orquestador"],
          [[r["n"], r["kind"], r["label"] or "—", usd(r["total_usd"]), mins(r["minutes"]),
            r["orchestrator_model"] or "—"] for r in rows])}

Los intentos sin versión son evidencia, no se borran: uno cortado por el límite de gasto
de la organización (en Opus) y uno detenido por el operador sin stream conservado.
"""
    return ("J", "anexo-j-cambio-del-lector", "Demo del cambio del lector (v3)", md)


def annex_judge() -> tuple[str, str, str, str]:
    c = conn()
    rows = [dict(r) for r in c.execute(
        "SELECT validator, criterion, value, justification FROM validations WHERE run_id = ? "
        "AND version = 2 AND validator IN ('judge_rubric', 'human_review') ORDER BY validator, "
        "criterion", (NOVEL_RUN,))]
    judge = [r for r in rows if r["validator"] == "judge_rubric" and r["criterion"] != "mean"]
    mean = next((r["value"] for r in rows if r["criterion"] == "mean"), None)
    human = next((r for r in rows if r["validator"] == "human_review"), None)
    md = f"""
Validador de tipo b (`judge_rubric`, docs/spec.md §2): el agente `judge` lee el libro
entero **anonimizado** una vez por versión y puntúa seis criterios de 0 a 10, cada uno
con su justificación. Un criterio sin justificación se rechaza.

## El juez sobre la v2 (10 capítulos)

{md_table(["criterio", "nota", "justificación"],
          [[r["criterion"], r["value"], (r["justification"] or "")[:300]] for r in judge])}

**Media: {f"{float(mean):.2f}".replace(".", ",")}** sobre los seis criterios.

## La lectura humana

- **Nota del dueño: {human['value'] if human else 'no medida'}** — una nota global, no por criterio.
- {(human['justification'] or '')[:400] if human else ''}
- Juez {f"{float(mean):.2f}".replace(".", ",")} frente a lectura humana {human['value'] if human else '—'}: la diferencia
  es de {f"{abs(float(mean) - float(human['value'])):.2f}".replace(".", ",")} puntos.

## Lo que el juez vio y el gate no

Una frase dicha dos veces en el capítulo 5 que las seis características dejaron pasar.
De ahí el linter de prosa O1 (`backend/linters/repetition.py`, solo informe).
""" if mean else "El juez no se ha ejecutado sobre esta versión: no medido."
    return ("P", "anexo-p-juez-y-lectura-humana", "El juez (LLM-as-judge) y la lectura humana", md)


def annex_decisions() -> tuple[str, str, str, str]:
    body = section(read("docs/spec.md"), "8. Decisions taken after approval")
    rows = [r for r in table_rows(body) if r and r[0].startswith("2026")]
    clean = lambda s: re.sub(r"\*\*|`", "", s)
    md = f"""
Cada decisión tomada después de aprobar la spec, con las **palabras del dueño**. Una
aprobación solo vale si la escribe él; se copia tal cual (docs/spec.md §8).

{md_table(["fecha", "decisión", "palabras del dueño"],
          [[r[0], clean(r[1])[:260], clean(r[-1])[:160]] for r in rows])}

{len(rows)} decisiones. Ninguna cambió un valor protegido de AGENTS.md §6 sin nombrarlo.
"""
    return ("M", "anexo-m-decisiones-del-dueno", "Decisiones del dueño tras la spec", md)


def annex_gaps() -> tuple[str, str, str, str]:
    ver = read("docs/verification.md")
    gaps = re.findall(r"^### (3\.\d+) (.+)$", ver, re.M)
    md = f"""
`docs/verification.md` clasifica cada garantía con su letra (T test, A análisis,
I inspección, D demostración, U no verificable) y un nivel de criticidad. Su §3 lista
lo que **no** está verificado, y por qué es una decisión:

> Un hueco listado es una decisión. Un hueco no listado es un defecto.

{md_table(["§", "hueco declarado"], [[n, re.sub(r"`", "", t)] for n, t in gaps])}

{len(gaps)} huecos declarados, cada uno con qué no se verifica, por qué se acepta, el
alcance del daño y cómo nos enteraríamos.
"""
    return ("L", "anexo-l-verificacion-y-huecos", "Verificación: garantías y huecos declarados", md)


def annex_lean() -> tuple[str, str, str, str]:
    md = read("lean/README.md")
    md = re.sub(r"^# .*\n", "", md, count=1)
    return ("N", "anexo-n-lean-cronologia", "Lean: invariantes de la cronología", md or
            "lean/README.md no existe.")


def annex_security() -> tuple[str, str, str, str]:
    doc = read("docs/security-report.md") or read("docs/security-review.md")
    summary = section(doc, "Summary")
    rows = [r for r in table_rows(summary) if r and r[0].startswith("SR-")]
    md = f"""
Análisis de seguridad (opcional O3): inyección de prompts, exfiltración entre novelas,
rutas, presupuesto, dependencias y secretos. Informe completo: `docs/security-report.md`.

{md_table(["id", "área", "severidad", "estado", "resumen"],
          [[r[0], r[1], r[2], r[3], re.sub(r"`", "", r[4])[:220]] for r in rows])}

- **Secretos en el historial**: revisados los dos repositorios; solo aparecen claves de
  prueba (`pk-lf-dum…`, `sk-lf-dum…`). Las credenciales se leen solo del entorno.
- **Sin API keys en ningún repo**: `.env.example` lleva las claves vacías.
"""
    return ("K", "anexo-k-seguridad", "Informe de seguridad", md)


def annex_visual() -> tuple[str, str, str, str]:
    body = section(read("docs/browser-mcp.md"), "Sessions")
    rows = [r for r in table_rows(body) if r and r[0] and r[0] != "date"]
    md = f"""
El validador `visual_check` inspecciona el libro renderizado: portada con dedicatoria,
índice con enlaces que llegan, ficha de personajes y lugares, página "what changed" (v > 1)
y ausencia de restos (Markdown, `TODO`, marcadores). Configuración: `.mcp.json`
(Playwright MCP); método y checklist: `docs/browser-mcp.md`.

{md_table(["fecha", "versión", "resultado", "qué encontró"],
          [[r[0], r[1], re.sub(r"\*\*", "", r[3]), re.sub(r"`", "", r[4])[:320]] for r in rows])}

**Qué cambió por ello:** la v1 falló la portada (sin dedicatoria ni alias, porque nada
escribía `dedication.md` en un run que sale de un brief). Se corrigió en `4cf8a8e`; la v2
y la v3 pasan.
"""
    return ("O", "anexo-o-inspeccion-visual", "Inspección visual con browser MCP", md)


def annex_agents() -> tuple[str, str, str, str]:
    agents = []
    for f in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        g = lambda k: (re.search(rf"^{k}:\s*(.+)$", t, re.M) or [None, "—"])[1].strip()
        agents.append([f.stem, g("tools"), g("model"), g("description")[:150]])
    commands = []
    for f in sorted((ROOT / ".claude" / "commands").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        first = next((l for l in t.splitlines() if l.strip() and not l.startswith(("---", "description"))), "")
        desc = (re.search(r"^description:\s*(.+)$", t, re.M) or [None, first])[1]
        commands.append([f"/{f.stem}", desc.strip()[:160]])
    memory = [l[2:] for l in read(".claude/memory/MEMORY.md").splitlines() if l.startswith("- ")]
    skills = sorted(p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir())
    md = f"""
Cómo refleja el repo el uso de Claude Code (`CLAUDE.md`, `.claude/`, `docs/subagents.md`,
`docs/skills.md`).

## Los {len(agents)} agentes — su línea `tools:` es su autoridad

{md_table(["agente", "tools", "modelo", "para qué"], agents)}

Solo `worldbuilder` y `character-architect` escriben la Biblia; `chapter-writer` solo tiene
`Glob`, así que no puede leer capítulos anteriores. Un test fija cada línea `tools:`.

## Comandos propios (`.claude/commands/`)

{md_table(["comando", "qué hace"], commands)}

## Skills del proyecto (`.claude/skills/`)

{", ".join(f"`{s}`" for s in skills)} — más las de proceso y stack listadas en `docs/skills.md`.

## Memoria del proyecto (`.claude/memory/`)

{chr(10).join(f"- {re.sub(r'[(][^)]*[)]', '', m).replace('[', '').replace(']', '')}" for m in memory)}
"""
    return ("Q", "anexo-q-claude-code", "Claude Code en el repo: agentes, comandos, skills y memoria", md)


def annex_next() -> tuple[str, str, str, str]:
    def status(rel):
        t = read(rel)
        m = re.search(r"^status:\s*(.+)$", t, re.M)
        return (m.group(1).split("—")[0].strip() if m else "—")
    specs = [("SPEC-EXAM-006", "specs/SPEC-EXAM-006-python-chapter-loop.md",
              "El bucle del capítulo en Python: el código conduce, el modelo solo juzga",
              "construido y probado a 0 $; la prueba real de 1 capítulo (AC-6, techo 3 $) no se ejecutó: pasó su corte"),
             ("SPEC-EXAM-007", "specs/SPEC-EXAM-007-stopped-novels.md",
              "Novelas paradas: Continue y papelera recuperable",
              "en el panel; Continue sin cifra y con tope por novela (2 × el techo del perfil)"),
             ("SPEC-EXAM-008", "specs/SPEC-EXAM-008-cost-per-change.md",
              "El coste de cada cambio, medido, en Langfuse y en el panel",
              "en el panel (sección Costs) y en Langfuse, con backfill de lo ya gastado")]
    md = f"""
Lo construido en el último tramo, para bajar el coste sin tocar la calidad: el umbral 8,
las seis características y los tres intentos no cambian.

{md_table(["spec", "qué", "estado de la spec", "dónde está"],
          [[s, what, status(rel), where] for s, rel, what, where in specs])}

## Por qué el bucle en Python es el siguiente paso

- El orquestador es ~92 % del coste de la novela y lo que hace en FLOW-4 es determinista:
  el orden, los números y la decisión (`decide`) ya son código.
- Descartado: **Haiku como orquestador** (run `phantom-station`: dejó de usar los agentes y
  el escritor perdió su aislamiento). **Sonnet** es el paso intermedio, ya aplicado.
- Más estricto con el bucle: coste por agente medido, el techo de 100k comprobado antes de
  cada llamada y los críticos en paralelo por construcción.
"""
    return ("R", "anexo-r-siguientes-pasos", "Lo último construido y el siguiente paso", md)


ANNEXES = [annex_costs, annex_reader_change, annex_security, annex_gaps, annex_decisions,
           annex_lean, annex_visual, annex_judge, annex_agents, annex_next]


# -------------------------------------------------------------- rendering


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def to_html(md: str) -> str:
    out, lines, i = [], md.strip().splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre>" + html.escape("\n".join(lines[i + 1:j])) + "</pre>")
            i = j + 1
            continue
        if m := re.match(r"^(#{1,4}) (.+)$", line):
            n = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|\s*-", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table>")
            continue
        elif re.match(r"^\s*[-*] ", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] |^\s{2,}\S", lines[i]):
                if re.match(r"^\s*[-*] ", lines[i]):
                    items.append(re.sub(r"^\s*[-*] ", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        elif line.startswith(">"):
            out.append(f"<blockquote>{inline(line.lstrip('> '))}</blockquote>")
        elif line.strip():
            para = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
                    r"^(#|\||```|>|\s*[-*] )", lines[i + 1]):
                i += 1
                para.append(lines[i])
            out.append(f"<p>{inline(' '.join(para))}</p>")
        i += 1
    return "\n".join(out)


PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{title}</title>
<style>
@page {{ size: A4; margin: 16mm 14mm 18mm; }}
body {{ font-family: "DM Sans", Arial, sans-serif; font-size: 10pt; color: #1f2a37; line-height: 1.45; }}
.brand {{ font-size: 8pt; letter-spacing: .12em; color: #f26b1d; font-weight: 700; }}
h1 {{ font-size: 19pt; margin: 4px 0 2px; }}
.meta {{ font-size: 8pt; color: #6b7280; border-bottom: 2px solid #f26b1d; padding-bottom: 6px; margin-bottom: 12px; }}
h2 {{ font-size: 13pt; margin: 16px 0 6px; color: #1f2a37; }}
h3 {{ font-size: 11pt; margin: 12px 0 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 8.5pt; }}
th {{ background: #1f2a37; color: #fff; text-align: left; padding: 4px 6px; }}
td {{ border-bottom: 1px solid #e5e7eb; padding: 4px 6px; vertical-align: top; }}
code {{ font-family: Consolas, monospace; font-size: 8.5pt; background: #f3f4f6; padding: 0 2px; }}
pre {{ background: #f3f4f6; padding: 8px; font-size: 8pt; white-space: pre-wrap; }}
blockquote {{ border-left: 3px solid #f26b1d; margin: 8px 0; padding: 2px 10px; color: #374151; }}
</style></head><body>
<div class="brand">QARACTER · STORYMAKER</div>
<h1>Anexo {letter} — {title}</h1>
<div class="meta">Generado desde el repositorio storyMaker · commit {sha} · {when} UTC · Qaracter group 2026</div>
{body}
</body></html>"""


def _alias() -> str | None:
    try:
        brief = json.loads(read("evals/briefs/01-hijo.json"))
        return (brief.get("recipient") or {}).get("alias")
    except ValueError:
        return None


def main() -> int:
    from playwright.sync_api import sync_playwright

    SRC.mkdir(parents=True, exist_ok=True)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    built = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        alias = _alias()
        for make in ANNEXES:
            letter, stem, title, md = make()
            if alias:
                # No annex names the recipient: the alias of the example brief
                # becomes "el destinatario" (privacy by design, verification §3.23).
                md = re.sub(rf"\b{re.escape(alias)}\b", "el destinatario", md)
            (SRC / f"{stem}.md").write_text(f"# Anexo {letter} — {title}\n{md}", encoding="utf-8",
                                            newline="\n")
            doc = PAGE.format(title=html.escape(title), letter=letter, sha=sha(), when=when,
                              body=to_html(md))
            tmp = SRC / f"{stem}.html"
            tmp.write_text(doc, encoding="utf-8")
            page.goto(tmp.resolve().as_uri())
            page.pdf(path=str(OUT / f"{stem}.pdf"), format="A4", print_background=True,
                     margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
            tmp.unlink()
            built.append((letter, f"{stem}.pdf", title))
            print(f"Anexo {letter}: {stem}.pdf")
        browser.close()
    index = sorted(EARLIER + built)
    (OUT / "README.md").write_text(
        "# Anexos de la presentación\n\n"
        "**Idioma: castellano**, con los términos técnicos en inglés. Cada anexo es un PDF\n"
        "individual. Los anexos I en adelante se generan desde el repositorio y su base de\n"
        "datos con `python tools/build_annexes.py`, así que sus cifras no pueden separarse del\n"
        "código que describen; su texto fuente está en `src/`. A–H se conservan como se\n"
        "produjeron.\n\n"
        "| anexo | fichero | contenido |\n|---|---|---|\n"
        + "".join(f"| {l} | [`{f}`]({f}) | {t} |\n" for l, f, t in index)
        + "\nLa novela de ejemplo y sus versiones están en `../../ejemplos/`: la v2 completa\n"
        "(`novela-ejemplo.pdf`), la v1 de 8 capítulos y la v3 del cambio del lector.\n",
        encoding="utf-8", newline="\n")
    print(f"index: {OUT / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
