# presentacion/

Lo que se entrega aquí (spec AC-13): el deck en **PDF y PPTX** con la identidad
Qaracter, la slide de presupuesto con los costes medidos, y el vídeo o su enlace.

| fichero | estado |
|---|---|
| `guion.md` | borrador del contenido slide a slide, con las cifras y su procedencia |
| `storymaker.pdf`, `storymaker.pptx` | pendiente — se montan en Claude Design desde `guion.md` |
| vídeo o enlace | pendiente — lo graba el dueño (spec §5) |

## Guion del vídeo (demo del cambio del lector, E8)

1. `dist/v1/novel.pdf` abierto: portada con la dedicatoria, índice, ficha de personajes (un clic lleva al primer capítulo).
2. El comprador cambia un dato del brief 01. Se muestra el comando y la fila de `fact_usage` que dice qué capítulos lo usan.
3. Sólo esos capítulos pasan otra vez por el gate (se ve en el panel o en `validations`).
4. `dist/v2/novel.pdf`: abre con la página de novedades; un clic en cada enlace lleva al capítulo cambiado, con el dato nuevo en el texto.
5. `dist/v1/` sigue ahí, sin tocar.
6. Cierre: coste medido de la regeneración frente al de la novela.

Tiene que poder grabarse el jueves por la noche.

## Email de entrega

Dos enlaces a commits (los dos repositorios) y una frase de diseño de tres líneas como máximo. Candidata, actualizada con el conductor por etapas:

> El escritor de cada capítulo no lee los anteriores y cada etapa arranca en un proceso limpio, así que nada pasa de 100.000 tokens y el capítulo 10 cuesta lo mismo que el 1; toda la continuidad pasa por una story bible en SQLite que sabe qué capítulo usa cada dato.

Alternativa más corta:

> La continuidad no está en el contexto del modelo sino en una story bible en SQLite que sabe qué capítulo usa cada dato; por eso un cambio del lector regenera sólo esos capítulos.
