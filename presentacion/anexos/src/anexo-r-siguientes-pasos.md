# Anexo R — Lo último construido y el siguiente paso

Lo construido en el último tramo, para bajar el coste sin tocar la calidad: el umbral 8,
las seis características y los tres intentos no cambian.

| spec | qué | estado de la spec | dónde está |
|---|---|---|---|
| SPEC-EXAM-006 | El bucle del capítulo en Python: el código conduce, el modelo solo juzga | approved | construido y probado a 0 $; la prueba real de 1 capítulo (AC-6, techo 3 $) no se ejecutó: pasó su corte |
| SPEC-EXAM-007 | Novelas paradas: Continue y papelera recuperable | approved | en el panel; Continue sin cifra y con tope por novela (2 × el techo del perfil) |
| SPEC-EXAM-008 | El coste de cada cambio, medido, en Langfuse y en el panel | approved | en el panel (sección Costs) y en Langfuse, con backfill de lo ya gastado |

## Por qué el bucle en Python es el siguiente paso

- El orquestador es ~92 % del coste de la novela y lo que hace en FLOW-4 es determinista:
  el orden, los números y la decisión (`decide`) ya son código.
- Descartado: **Haiku como orquestador** (run `phantom-station`: dejó de usar los agentes y
  el escritor perdió su aislamiento). **Sonnet** es el paso intermedio, ya aplicado.
- Más estricto con el bucle: coste por agente medido, el techo de 100k comprobado antes de
  cada llamada y los críticos en paralelo por construcción.
