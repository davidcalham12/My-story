# Anexo P — El juez (LLM-as-judge) y la lectura humana

Validador de tipo b (`judge_rubric`, docs/spec.md §2): el agente `judge` lee el libro
entero **anonimizado** una vez por versión y puntúa seis criterios de 0 a 10, cada uno
con su justificación. Un criterio sin justificación se rechaza.

## El juez sobre la v2 (10 capítulos)

| criterio | nota | justificación |
|---|---|---|
| character_coherence | 9 | Every character maintains consistent personality and behavior across all appearances. The protagonist develops believably—introduced claiming fearlessness (Ch1) but revealed to experience genuine anxiety about darkness and being lost (Ch5), with growth earned through direct experience rather than su |
| continuity | 8 | The book maintains consistent facts and timeline across all ten chapters—the protagonist's birthday (Ch1) leads to the quest (Ch5), the overnight visit to Elena's house (Ch6), and the reintegration (Ch7-10) follow logically. Character details persist (Bruno's habits, Captain Crunch the fossil, the l |
| narrative_arc | 8 | The book traces a complete arc from curiosity and setup (Ch1-4), through adventure and discovery (Ch5-6), to integration and transformed understanding (Ch7-10). The central promise established in Ch1—what lies beyond the hill—is fulfilled through the encounter with Elena's house and Elena herself. T |
| natural_personalisation | 8 | Despite the anonymized placeholder name, the protagonist is written as a fully-realized character with distinct consciousness, agency, and specific concrete details: a loyal dog with his own fears and growth arc, a fossil collection (Captain Crunch, the smooth river stone), a particular family struc |
| pacing | 8 | The ten chapters are well-proportioned to their narrative weight. Setup chapters (Ch1-4) build appropriately toward the turning point; the climb itself (Ch5) is the longest chapter and carries both the physical climax and the emotional turning point. The night away (Ch6) moves quickly, serving its f |
| tone | 9 | The book achieves and sustains the requested warm, funny, and gentle tone throughout all ten chapters. Ch1 establishes intimate coziness (honey on tables, Bruno sleeping without permission). Ch3 demonstrates humor through Marcos's evasive storytelling and the protagonist's frustrated response. Ch5's |

**Media: 8,33** sobre los seis criterios.

## La lectura humana

- **Nota del dueño: 8** — una nota global, no por criterio.
- The owner read the complete ten-chapter book (v2) on 2026-09-24 and scored it a solid 8 overall. The owner gave one overall score, not one per criterion; the comparison is therefore overall against the judge mean: human 8, judge 8.33, a difference of 0.33 in the same direction.
- Juez 8,33 frente a lectura humana 8: la diferencia
  es de 0,33 puntos.

## Lo que el juez vio y el gate no

Una frase dicha dos veces en el capítulo 5 que las seis características dejaron pasar.
De ahí el linter de prosa O1 (`backend/linters/repetition.py`, solo informe).
