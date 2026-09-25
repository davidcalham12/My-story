# Guion de la presentación — storyMaker

Para el deck de 18 slides (`storymaker-deck.pdf` / `.pptx`, y en Claude Design).
Duración: unos **15 minutos** de presentación, **8 de demo** y el tiempo que quede
para preguntas.

Cómo usar este guion:
- Lo que va entre comillas es **lo que se dice**, casi literal. Léelo en voz alta
  dos o tres veces y después dilo con tus palabras.
- Debajo de cada slide, **las cifras que tienes que saber** y **la frase puente**
  a la siguiente.
- El deck está en **comunicación piramidal**: primero la respuesta, luego las
  tres razones que la sostienen (funciona, es fiable, el coste se conoce) y cada
  razón con sus pruebas. Si te pierdes, vuelve a la estructura: *¿en qué razón
  estoy y qué prueba estoy enseñando?*

Actualizado: 2026-09-25, con el deck final de 18 slides.

---

## Parte 1 — La presentación (≈ 15 min)

### Slide 1 · Portada (15 s)

"Buenos días. Desde Qaracter os presentamos storyMaker: novelas personalizadas
para regalar, escritas por un sistema de agentes que se comprueba a sí mismo."

**Puente:** "Empiezo por la conclusión."

### Slide 2 · La respuesta, primero (1 min 15 s)

"Os traemos una respuesta y tres razones.

La respuesta: **storyMaker entrega una novela personalizada de diez capítulos,
comprobada, y con un coste medido.**

Primera razón: **funciona.** Hay una web donde se pide, se lee y se corrige, y
una novela de ejemplo real: diez capítulos, un juez automático le dio 8,33 sobre
10 y la revisión humana un 8. Cuando el lector cambió un dato, solo se
reescribieron los dos capítulos que lo usaban.

Segunda: **es fiable.** Cada cosa que el sistema promete la comprueba alguien que
no la escribió. Hay trece agentes con una tarea cada uno, y ningún capítulo entra
en el libro sin sacar al menos un 8 en seis criterios.

Tercera: **sabemos lo que cuesta.** 74,20 dólares medidos por novela, y sabemos
exactamente dónde se va el dinero y cómo bajarlo.

El resto de la presentación demuestra cada una de las tres, en este orden."

**Cifras:** 10 capítulos · juez 8,33 · humano 8 · 2 capítulos reescritos · 13
agentes · nota mínima 8 en 6 criterios · 74,20 $.

**Puente:** "Antes, treinta segundos sobre lo que pide el cliente."

### Slide 3 · El cliente (30 s)

"Páginas de Regalo vende regalos. Quien compra es un padre, una pareja, un hijo
o un compañero de trabajo, y quiere que la persona que lo recibe **se reconozca**:
su nombre, sus recuerdos, sus manías. Y que el libro se lea de principio a fin
sin tropezar: sin un personaje que cambia de carácter, sin saltos de tiempo, sin
un final cortado.

En concreto: diez capítulos de entre 1.000 y 1.500 palabras, en PDF, y poder
corregir un dato después."

**Puente:** "Primera razón: funciona. Os lo enseño."

### Slide 4 · 1 · Funciona — la web (1 min)

"Esta es la web, tal como está funcionando. Arriba, el estado en una frase:
cuántas novelas se están escribiendo, cuántas están listas y cuántas se han
parado. Debajo, una tarjeta por novela.

El comprador hace cuatro cosas desde aquí:
- **pedir**: 'Order a new novel' abre la entrevista con los datos, los
  recuerdos, el tono, las palabras prohibidas y los hechos que tienen que salir;
- **seguir**: cada tarjeta dice si la novela se está escribiendo, está lista o
  se paró, y dónde;
- **leer y corregir**: 'Open' muestra el libro, lo descarga en PDF y permite
  pedir un cambio;
- y si una novela se paró, **continuarla** desde donde quedó, sin empezar de
  cero, o mandarla a la papelera.

La primera tarjeta es nuestra novela de ejemplo, lista para leer."

**Si preguntan cómo está hecha:** React en el navegador, un servidor FastAPI en
Python que lanza el sistema de agentes y lo guarda todo en SQLite.

**Puente:** "Y esto es lo que recibe la persona."

### Slide 5 · 1 · Funciona — el libro (45 s)

"El libro llega con portada y dedicatoria, un índice donde cada capítulo es un
enlace, y esta ficha: los personajes y los lugares, cada uno con el capítulo
donde aparece por primera vez.

Esa ficha no la escribe un modelo al final: sale de la **story bible**, la base
de datos donde el sistema guarda cada hecho, cada personaje y en qué capítulo se
usa. Y lo comprobamos en un navegador real: la versión 2 y la 3 pasan la revisión
visual."

**Puente:** "Y ahora lo más interesante: qué pasa cuando el lector cambia algo."

### Slide 6 · 1 · Funciona — el cambio del lector (1 min 15 s)

"El comprador se da cuenta de que el observatorio que el niño construyó con su
abuelo no era de cartón: era una **casa del árbol**. Lo cambia en la web.

El sistema consulta la story bible, que sabe que ese dato aparece en los
capítulos 3 y 10. **Solo esos dos se reescriben**, y pasan otra vez por el mismo
control de calidad que el resto.

Sale la versión 3. A la izquierda, su primera página: qué cambió y qué capítulos
se reescribieron. La versión 2 se queda intacta. A la derecha, el capítulo 3
nuevo: ya habla de la casa del árbol.

Costó 10,31 dólares medidos y unos 46 minutos."

**Si hay vídeo, se pone aquí.**

**Puente:** "Eso es lo que funciona. Segunda razón: por qué es fiable. Y empieza
por una decisión."

### Slide 7 · 2 · Es fiable — la decisión clave (1 min)

"La decisión que lo sostiene todo: **el escritor nunca puede leer los capítulos
anteriores.**

No es que se lo pidamos en un prompt: es que su única herramienta devuelve
nombres de ficheros, nunca su contenido. Entonces, ¿cómo sabe lo que pasó antes?
Por la story bible y por un resumen corto de lo ocurrido.

¿Por qué importa? Porque así el capítulo 10 pesa lo mismo que el 1: no es más
caro ni más lento, el contexto nunca se llena y nada pasa del límite de 100.000
tokens. Toda la continuidad pasa por la story bible."

**Puente:** "Veamos el recorrido completo de una novela."

### Slide 8 · 2 · Es fiable — el recorrido (1 min 15 s)

"Una novela recorre siete etapas, siempre en este orden:
0, la entrevista convierte lo que escribe el comprador en un pedido validado;
1, se escriben las reglas del mundo;
2, los personajes y la cronología;
3, el guion capítulo a capítulo, que un auditor revisa antes de escribir nada;
4, diez veces: se escribe cada capítulo y se critica;
5, se unifica la voz;
6, un juez lee el libro entero y se genera el PDF.

Tres piezas lo mantienen en orden:
- el **orquestador**, Claude Code, sigue un procedimiento escrito y llama a cada
  agente en su etapa; no escribe la novela;
- la **puerta de calidad**: cada capítulo necesita al menos un 8 en seis
  criterios; tiene tres intentos con una hoja de correcciones y, si no pasa, la
  novela se para: nunca entra un capítulo malo;
- y **dos hooks**: scripts que se ejecutan solos cada vez que se escribe un
  capítulo, para validarlo y para buscar palabras prohibidas.

Como cada etapa deja su resultado en disco, si algo falla se retoma desde ahí."

**Los seis criterios:** continuidad, reglas del mundo, guion, prosa, longitud y
que el modelo no deje comentarios suyos en el texto. Los cuatro primeros los
juzga un modelo; los dos últimos, código.

**Puente:** "¿Quién hace cada cosa? Trece agentes."

### Slide 9 · 2 · Es fiable — los agentes que crean (1 min)

"Son trece agentes y cada uno hace una sola cosa. Siete crean el libro:
- el **entrevistador** convierte lo que escribe el comprador en el pedido y
  pregunta lo que falta; no decide nada;
- el **constructor del mundo** escribe sus reglas;
- el **arquitecto de personajes** escribe el reparto, la cronología y los
  misterios; solo estos dos pueden escribir la story bible;
- el **arquitecto del guion** escribe qué pasa en cada capítulo;
- el **escritor** escribe un capítulo cada vez, sin leer los anteriores;
- el **editor de estilo** unifica la voz, pero no puede cambiar ni una palabra;
- y el **editor** escribe la sinopsis de contraportada; el libro lo arma el
  código.

Todos corren en Haiku, el modelo más barato."

**Puente:** "Y seis lo comprueban."

### Slide 10 · 2 · Es fiable — los agentes que comprueban (1 min)

"La regla es que **quien escribe no se evalúa a sí mismo**. Seis agentes
comprueban:
- el de **continuidad** compara el capítulo con la story bible;
- el de **reglas del mundo** comprueba que las respeta, y además audita el guion
  antes de empezar;
- el de **guion** comprueba que el capítulo hace lo que le tocaba, en orden;
- el de **prosa** juzga cómo está escrito: párrafos que no avanzan, diálogos
  genéricos, repeticiones;
- uno opcional hace los tres primeros en una sola lectura, para gastar menos;
- y el **juez** lee el libro entero una vez y lo puntúa en seis criterios.

Y lo importante: **los críticos solo informan. Quien decide si un capítulo entra
es código**: toma la nota más baja y la compara con 8."

**Si preguntan "¿y si el modelo se inventa la nota?":** "Una respuesta mal
formada no cuenta como aprobado, la decisión es código, y una auditoría la
recalcula después de cada novela."

**Puente:** "Esas son las personas. Veamos los controles."

### Slide 11 · 2 · Es fiable — validación (1 min)

"Tenemos cuatro tipos de validadores, y cada uno actúa en un punto fijo:
- **programáticos**, que son código y siempre dan el mismo resultado: el
  formato del pedido, los nombres exactos, la longitud, los hechos obligatorios,
  las palabras prohibidas y la revisión visual;
- **semánticos**, que juzga un modelo o una persona: los críticos, el juez y la
  revisión humana;
- **formal sobre la historia**: Lean comprobaría la cronología; no se ejecutó
  porque no se instala sin permisos de administrador, y así lo declaramos;
- **formal sobre el sistema**: describimos el sistema en TLA+ y el comprobador
  revisó 18.253 estados sin errores: nada sin validar se publica, reanudar no
  duplica, la versión anterior se conserva y siempre termina.

El principio: **lo que se puede comprobar con un script, se comprueba con un
script**; los modelos solo juzgan donde hace falta juicio."

**Puente:** "Y todo esto queda registrado."

### Slide 12 · 2 · Es fiable — formal y observabilidad (1 min)

"Un sistema fiable no es el que nunca falla: es el que **se entera** cuando
falla. Todo queda registrado en SQLite y en Langfuse: cada novela es una sesión,
cada versión una traza y cada validador una nota.

Y el registro nos delató tres fallos reales, que corregimos:
- con el orquestador en el modelo barato, dejó de usar nuestros agentes y el
  escritor perdió su aislamiento; por eso el orquestador no va en Haiku;
- con un techo de gasto demasiado bajo, cerró una novela sin pasar el control
  de calidad; lo cazó la auditoría y subimos el techo;
- y la configuración decía un modelo y corrió otro; lo vimos en el registro de
  coste.

Además, la entrevista rechazó un pedido con un recuerdo fechado antes de que la
persona naciera, sin gastar un céntimo."

**Puente:** "Por último en esta parte: lo que no debe salir."

### Slide 13 · 2 · Es fiable — guardrails (1 min)

"Cuatro barreras:
- **palabras prohibidas** en tres niveles: para todos, para este cliente y para
  esta novela; da igual mayúsculas, tildes o plural; si aparece una, el capítulo
  vuelve al escritor. Resultado: cero apariciones en los tres libros publicados;
- **inyección**: el texto libre del comprador nunca es una orden; lo probamos
  con un pedido trampa que decía 'ignora tus instrucciones' y no llegó al libro;
- **datos personales**: el modelo nunca ve el nombre real del destinatario; el
  código lo pone al publicar, y no hay ninguna clave en el repositorio;
- y un **registro de auditoría** de cada decisión."

**Puente:** "Tercera razón: el coste."

### Slide 14 · 3 · Coste conocido — presupuesto (1 min)

"Aquí siempre distinguimos lo **medido** de lo **supuesto**.

Medido: la novela de diez capítulos costó **74,20 dólares**, en 169 minutos. Sale
del propio registro de Claude Code, no de una estimación.

Supuesto, para validar con vosotros: 6 dólares de infraestructura por novela y un
precio de venta de 129. Con eso queda un **margen del 38 %**.

La tabla muestra el margen mensual con 20, 100 y 500 novelas al mes, y qué pasa
si los tokens suben un 50 % o si todos los capítulos necesitan el tercer
intento: en todos los casos sigue habiendo margen."

**Cuenta, por si la piden:** 129 − 74,20 − 6 = 48,80 $ → 38 %.

**Puente:** "Y lo más útil: dónde se va ese dinero."

### Slide 15 · 3 · Coste conocido — dónde se va (1 min)

"De los 74,20 dólares, **los agentes que escriben y critican son solo el 8 %**:
6,07 dólares. **El 92 % es el orquestador**: 68,13 dólares.

¿Por qué? Porque el orquestador es un modelo que relee el procedimiento en cada
turno para decidir cosas que ya son reglas. Abaratar los agentes ya no mueve la
cifra: lo que hay que abaratar es el orquestador.

Ya se nota: en el cambio del lector, con el orquestador en un modelo más barato,
un capítulo costó 4,57 dólares frente a los 7,52 de antes."

**Puente:** "Y eso nos lleva al siguiente paso, que ya está aprobado."

### Slide 16 · 3 · Coste conocido — siguiente paso (45 s)

"**El código conduce; el modelo solo juzga.** Hoy un modelo decide el bucle de
cada capítulo: escribir, criticar, reintentar. Con el siguiente paso, ese bucle
lo ejecuta código en Python: escritor, los cuatro críticos en paralelo, nota
mínima y reintento. Los agentes siguen siendo los mismos y el listón no cambia:
8, seis criterios y tres intentos.

Está construido y aprobado; lo que falta es medirlo en una novela real. Y lo que
descartamos: poner el orquestador en el modelo barato, porque ya vimos que rompe
el aislamiento del escritor."

**Puente:** "Vuelvo al principio."

### Slide 17 · En resumen (1 min)

"La respuesta era: storyMaker entrega una novela personalizada de diez
capítulos, comprobada y con un coste medido. Y lo hemos visto:
- **funciona**: una novela real, un 8,33 del juez y un cambio que reescribió
  solo dos capítulos;
- **es fiable**: trece agentes, y quien decide si un capítulo entra es código;
- **sabemos lo que cuesta**: 74,20 dólares, el 92 % en el orquestador, y el paso
  que lo reduce ya está listo.

Los riesgos, dichos con claridad: el coste depende del orquestador; el juez es un
modelo y no siempre da la misma nota; los hechos obligatorios se buscan por texto
literal; y tres capítulos se quedaron un poco por debajo de las 1.000 palabras.

Además del mínimo hemos hecho un servidor MCP de solo lectura, una revisión de
seguridad, un linter de prosa y un segundo modelo TLA+ que encontró un fallo
real. Los siguientes pasos: el bucle en código por defecto, login y un lector web
donde se pueda seleccionar el texto."

### Slide 18 · Gracias (10 s)

"Gracias. Ahora os lo enseño en directo, y después, las preguntas que queráis."

---

## Parte 2 — Demo en directo (≈ 8 min)

Panel en `http://localhost:5191`, servidor en `:8000`. **Antes de empezar:**
comprueba que la biblioteca carga y que no hay ningún orquestador vivo.

1. **Biblioteca.** "Esta es la biblioteca: novelas listas, en curso y paradas."
2. **Abrir *The Other Side of the Hill* → Progress.** "Está lista. Aquí el coste,
   y si despliego el detalle, la nota de cada capítulo y cuántos intentos
   necesitó."
3. **Read.**
   - "El libro, con portada, dedicatoria e índice."
   - Pulsa un personaje en la ficha: "y salta al capítulo donde aparece".
   - Cambia entre la versión 1, la 2 y la 3: "todas las versiones se conservan".
   - **Download PDF**: "y se descarga con el título del libro".
4. **Ask for a change.** Elige el hecho del observatorio, escribe "a wooden
   treehouse observatory" y enseña que se reescribirían los capítulos 3 y 10
   **antes de gastar nada**. "Esto ya lo ejecutamos: es la versión 3." Abre su
   página de novedades.
5. **New novel.** Pulsa "Fill this in with the example brief", enseña los pasos,
   la longitud de 1 a 10 y el aviso de datos que faltan. **No pulses Order en
   directo**: cuesta dinero real y tarda.
6. **Langfuse.** Una traza de la novela, con sus llamadas y sus notas.

**Si algo falla en directo:** abre `ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`
o pon el vídeo, que muestra el mismo recorrido.

---

## Parte 3 — Preguntas difíciles, con respuesta corta

| pregunta | respuesta |
|---|---|
| ¿Por qué no un solo modelo que escriba todo el libro? | Porque se contradice, repite y olvida lo pedido, y cada capítulo le cuesta más que el anterior. Separar escritor y críticos, y darles la story bible, lo evita. |
| ¿Cómo sabe el escritor lo que pasó antes? | Por la story bible (hechos, personajes, cronología) y un resumen de lo ocurrido de como mucho 260 palabras. Nunca por los capítulos anteriores. |
| ¿Y si el juez o un crítico se equivocan? | Los críticos solo informan; la decisión es código. El juez no bloquea: informa por versión, y lo contrastamos con la revisión humana (8,33 frente a 8). |
| ¿Por qué 1 capítulo en las evaluaciones? | Cinco novelas completas costaban unos 250 $ y no daban tiempo; cada validador se ejercita igual con un capítulo. La novela de ejemplo sí tiene 10. Está declarado. |
| ¿Por qué no se ejecutó Lean? | Su instalador necesita permisos de administrador en la máquina, que no teníamos. El export está escrito y el motivo, declarado. |
| ¿Por qué hechos obligatorios da 1 de 3? | La comprobación busca el texto literal: "tomato plants" no cuenta como "the tomatoes". Preferimos marcar un hecho como no cubierto antes que darlo por bueno sin estarlo. |
| ¿Tres capítulos por debajo de 1.000 palabras? | Tienen entre 934 y 967. El control acepta un 10 % de tolerancia; el enunciado pide 1.000. Lo declaramos como riesgo. |
| ¿Por qué el orquestador no va en Haiku, si es más barato? | Lo probamos: dejó de usar nuestros agentes y el escritor tuvo acceso a todo. Por eso el ahorro viene de pasar el bucle a código, no de un modelo más barato. |
| ¿Cómo se protegen los datos personales? | El modelo nunca ve el nombre real: el código lo pone al publicar. Las credenciales salen del entorno y no hay claves en el repositorio. |
| ¿Qué pasa si se cae a mitad? | Cada etapa deja su resultado en disco; se continúa desde la primera sin terminar, sin repetir lo hecho. |

---

## Chuleta — las cifras de memoria

| qué | cifra |
|---|---|
| capítulos por novela | 10, de 1.000 a 1.500 palabras |
| agentes | 13 (7 crean, 6 comprueban), todos en Haiku |
| puerta de calidad | nota mínima 8 en 6 criterios, 3 intentos |
| juez / revisión humana | 8,33 / 8 |
| coste de la novela | 74,20 $ medidos, 169 min, 468 turnos |
| dónde se va | 92 % orquestador (68,13 $), 8 % agentes (6,07 $) |
| cambio del lector (v3) | capítulos 3 y 10, 10,31 $, 46 min |
| margen | 38 % con precio de 129 $ e infraestructura de 6 $ (supuestos) |
| techo de gasto | 60 $ por novela |
| TLA+ | 18.253 estados sin errores |
| palabras prohibidas en los libros | 0 |
