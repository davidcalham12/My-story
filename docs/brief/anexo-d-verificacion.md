NovaForge v2 — Anexo D: principios de verificación (best effort)
Complemento de NOVAFORGE-V2-BRIEF.md §2.2 y D26, y de los Anexos B y C. Añade lo que faltaba al planteamiento de verification.md: el criterio, no sólo la mecánica. Se aplica al construir la skill verification y al escribir el documento.

Fecha: 2026-09-22.

1. El principio que gobierna el documento
Diseñar soluciones con IA es un ejercicio de BEST EFFORT. La habilidad de un buen ingeniero de soluciones IA reside en conseguir crear sistemas confiables. — la profesora

Va como epígrafe de verification.md. Su consecuencia práctica: la fiabilidad no viene de que nada falle, sino de saber exactamente dónde puede fallar, qué pasa cuando falla, y cómo nos enteramos. Un sistema con huecos conocidos y acotados es confiable. Un sistema "sin huecos" es un sistema cuyos huecos nadie ha buscado.

El brief ya decía "lo no medible se dice no medible, nunca cero". Esto lo generaliza: lo no verificado se escribe, nunca se omite.

2. Lo que verification.md tiene que contener, además de las letras
El principal pedía, por garantía: qué promete, letra T/A/I/D/U, método, evidencia. Se añaden cuatro cosas.

2.1 Nivel de criticidad por garantía
Cada garantía lleva un nivel, y el nivel fija la letra mínima aceptable:

nivel	qué significa	letra mínima
crítica	si se rompe, la tesis del proyecto o la seguridad caen	T o A. Si sólo se puede I o D, es un riesgo asumido y va en §2.2
importante	si se rompe, el resultado empeora de forma visible	I como mínimo
accesoria	si se rompe, se arregla después sin daño	cualquiera, incluida U
No todo merece el mismo esfuerzo. Saber a qué darle importancia es la mitad del trabajo; esta columna es donde se escribe esa decisión.

Asignación inicial para las dieciséis garantías de §5 del principal:

Críticas: 1 (sin prosa previa), 4 (patch_then_halt, nunca con advertencias), 8 (sólo dos agentes escriben la Biblia), 13 (techo de presupuesto), 16 (seguridad y credenciales).
Importantes: 2 (100k), 3 (cinco notas ≥ 8), 5 (reglas del redraft), 6 (la hoja), 9 (libro ensamblado en código), 10 (auditoría del guion), 11 (procedencia), 12 (coste no inventado).
Accesorias: 7 (lo prohibido de §8.3 como lista), 14 (género desde la premisa), 15 (rangos con criterio).
La sesión constructora puede mover una garantía de nivel, escribiendo por qué.

2.2 Sección "Huecos conocidos y riesgos asumidos"
La sección más importante del documento, y la que faltaba. Una tabla, una fila por hueco:

campo	qué va
qué no está verificado	en una frase
por qué se acepta	coste de verificarlo, o imposibilidad
alcance del daño	qué se rompe si falla, y hasta dónde llega
cómo nos enteraríamos	la señal que lo delata: un log, una métrica, un usuario
quién lo revisa y cuándo	o "nadie, y se acepta"
La regla: un hueco que está en esta tabla es una decisión de ingeniería. Un hueco que no está es un defecto. Por eso esta sección se revisa en cada spec: agents.md §4.3 exige que cada SPEC-NNN liste los huecos que deja, y de ahí pasan aquí.

Huecos que ya se conocen y entran de inicio:

Tres de las cinco notas del gate las pone un modelo. No reproducen. Alcance: un capítulo aceptado hoy podría no serlo mañana. Señal: los instrumentos de LOOP-003 miden la dispersión entre runs. Se acepta: es la naturaleza del juicio literario.
El tope de 100k no se puede reservar antes de despachar (Anexo C §3). Alcance: una llamada puede superar el tope antes de que Python la pare. Señal: halted: context en el log. Se acepta: sin API key no hay conteo previo; la estimación en SKILL.md es la primera línea.
Los agentes no saben medir su propio trabajo. El worldbuilder declaró 870 palabras cuando eran 948. Alcance: cualquier cifra autodeclarada. Señal: el orquestador mide con wc -w, nunca cree al agente. Se acepta y se neutraliza: ninguna autodeclaración entra en una decisión.
Un crítico puede emitir un hallazgo falso. Ocurrió: un 3/10 por una cuenta mal hecha. Alcance: una corrección innecesaria que estropea texto correcto. Señal: el arbitraje del orquestador y los late_findings. Se acepta con mitigación: los hallazgos numéricos se recomputan.
Nadie mide la calidad de la prosa. Alcance: frases duplicadas o fallos visibles publicados, ya ocurrió tres veces. Señal: ninguna automática. Se acepta en v1: es Unverifiable con los medios actuales; va a v2 como sexta característica si se decide.
El procedimiento de SKILL.md no se prueba a $0. Alcance: un cambio en el procedimiento sólo se valida con un run real. Señal: los --self-test de los instrumentos y el run tiny de la Fase 3. Se acepta: es el precio de no tener API key.
Un run interrumpido no se reanuda. Alcance: se pierde lo gastado. Señal: halted: process. Se acepta en v1.
2.3 Regla "código antes que agente"
Cuando una comprobación se puede hacer con un script, se hace con un script. Un agente sólo juzga donde hace falta juicio. Cada vez que algo pasa de agente a código, se anota aquí, porque es una mejora de fiabilidad y de coste a la vez.

Ya aplicado en el proyecto, y hay que escribirlo:

comprobación	era	es
longitud del capítulo	—	wc -w del orquestador
encabezado del capítulo	—	script
validez de la hoja de retroalimentación	criterio del orquestador	validate-sheet, rechaza antes de enviar
ensamblado del libro	un agente (parafraseaba)	concatenación en shell
aplicación de las correcciones	el escritor reescribía	sustituciones {find, replace} literales
beats del guion contra las reglas del mundo	nada	auditoría por script antes de FLOW-4 (D25)
hallazgos aritméticos de los críticos	se creían	se recomputan
Candidatos siguientes: el conteo de hechos del resumen; la detección de ## a principio de párrafo; la comprobación de nombres canónicos.

2.4 Cada validador dice qué propagación frena
Un validador no "comprueba": impide que un fallo llegue al siguiente paso. Por cada uno se escribe qué frena:

validador	frena que…
validate-sheet	una hoja incompleta o que cita prosa previa llegue al escritor
auditoría del guion	un beat imposible llegue a FLOW-4 y mate el run tres intentos después
measure	una afirmación sin medir llegue a la documentación
test del front matter del escritor	un cambio de herramientas llegue a un run
vigilante de coste	un run llegue a $49 sin que nadie lo decida
validador SKILL.md ↔ flow.yaml	el procedimiento y el contrato diverjan en silencio
3. Qué cambia en la skill verification (§2.2 del principal)
La skill, dado el contexto, genera verification.md con estas secciones y en este orden:

Epígrafe (§1).
Tabla de garantías: promesa · nivel · letra · método · evidencia.
Huecos conocidos y riesgos asumidos (§2.2), con sus cinco campos.
Código antes que agente (§2.3).
Qué frena cada validador (§2.4).
Qué cambió desde la versión anterior.
Criterio de la skill, ampliado: preferir la letra más fuerte que sea cierta; declarar Unverifiable sin vergüenza; una garantía crítica con letra I o D genera automáticamente una fila en huecos; y nunca quitar una fila de huecos sin sustituirla por la evidencia que lo cerró.

4. Qué cambia en agents.md (Anexo B §4)
§4.3, paso 2: la spec lista también los huecos que deja y su nivel.
§4.4, definición de hecho: verification.md actualizado, incluida la tabla de huecos, si el cambio abre o cierra uno.
Regla nueva: antes de proponer un agente para una tarea, decir por qué no sirve un script. Si sirve, es un script.
5. Qué decirle a la sesión constructora
Para verification.md: añade el epígrafe de la profesora (best effort), un nivel de criticidad por garantía que fija la letra mínima, y sobre todo una sección de huecos conocidos y riesgos asumidos con cinco campos por fila: qué no está verificado, por qué se acepta, alcance del daño, cómo nos enteraríamos, quién lo revisa. Un hueco listado es una decisión; uno no listado es un defecto. Añade también la tabla de "código antes que agente" y, por cada validador, qué propagación frena. Detalles y los siete huecos iniciales en el Anexo D.