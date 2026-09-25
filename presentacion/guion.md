# Guion de la presentación — storyMaker

Para el deck de 18 slides (`storymaker-deck.pdf` / `.pptx`, y en Claude Design).
Presenta una sola persona. Duración: unos **15 minutos** de presentación, **8 de
demo** y el tiempo que quede para preguntas.

Cómo usar este guion:
- Lo que va entre comillas es **lo que se dice**, casi literal. Léelo en voz alta
  dos o tres veces y después dilo con tus palabras.
- Debajo de cada slide están **las cifras que tienes que saber** y **la frase
  puente** a la siguiente.
- El deck sigue la **comunicación piramidal**: primero la respuesta, luego las
  tres razones que la sostienen (funciona, es confiable, el costo se conoce) y
  cada razón con sus pruebas. Si te pierdes, vuelve a la estructura: *¿en qué
  razón estoy y qué prueba estoy mostrando?*

Actualizado: 2026-09-25, con el deck final de 18 slides.

---

## Parte 1 — La presentación (≈ 15 min)

### Slide 1 · Portada (15 s)

"Buenos días. Les presento storyMaker, de Qaracter: novelas personalizadas para
regalar, escritas por un sistema de agentes que se revisa a sí mismo."

**Puente:** "Empiezo por la conclusión."

### Slide 2 · La respuesta, primero (1 min 15 s)

"Les traigo una respuesta y tres razones.

La respuesta: **storyMaker entrega una novela personalizada de diez capítulos,
revisada y con un costo medido.**

Primera razón: **funciona.** Hay una página web donde se pide, se lee y se
corrige, y una novela de ejemplo real: diez capítulos, un juez automático le dio
8.33 sobre 10 y mi revisión humana, un 8. Cuando el lector cambió un dato, solo
se reescribieron los dos capítulos que lo usaban.

Segunda: **es confiable.** Todo lo que el sistema promete lo revisa alguien que
no lo escribió. Hay trece agentes con una tarea cada uno, y ningún capítulo entra
al libro sin sacar por lo menos un 8 en seis criterios.

Tercera: **sé cuánto cuesta.** 74.20 dólares medidos por novela, y sé
exactamente en qué se va el dinero y cómo bajarlo.

El resto de la presentación demuestra cada una de las tres, en este orden."

**Cifras:** 10 capítulos · juez 8.33 · humano 8 · 2 capítulos reescritos · 13
agentes · calificación mínima 8 en 6 criterios · 74.20 dólares.

**Puente:** "Antes, treinta segundos sobre lo que pide el cliente."

### Slide 3 · El cliente (30 s)

"Páginas de Regalo vende regalos. Quien compra es un papá, una pareja, un hijo o
un compañero de trabajo, y quiere que la persona que lo recibe **se reconozca**:
su nombre, sus recuerdos, sus manías. Y que el libro se lea de principio a fin
sin tropezar: sin un personaje que cambia de carácter, sin saltos de tiempo, sin
un final cortado.

En concreto: diez capítulos de entre 1,000 y 1,500 palabras, en PDF, y poder
corregir un dato después."

**Puente:** "Primera razón: funciona. Se los muestro."

### Slide 4 · 1 · Funciona — la web (1 min)

"Esta es la página web, funcionando. Arriba, el estado en una frase: cuántas
novelas se están escribiendo, cuántas están listas y cuántas se detuvieron.
Abajo, una tarjeta por novela.

Desde aquí el comprador hace cuatro cosas:
- **pedir**: 'Order a new novel' abre la entrevista con los datos, los
  recuerdos, el tono, las palabras prohibidas y los hechos que tienen que
  aparecer;
- **seguir**: cada tarjeta dice si la novela se está escribiendo, si está lista
  o si se detuvo, y en qué punto;
- **leer y corregir**: 'Open' muestra el libro, lo descarga en PDF y permite
  pedir un cambio;
- y si una novela se detuvo, **continuarla** desde donde se quedó, sin empezar de
  cero, o mandarla a la papelera.

La primera tarjeta es mi novela de ejemplo, lista para leer."

**Si preguntan cómo está hecha:** React en el navegador, un servidor FastAPI en
Python que lanza el sistema de agentes y guarda todo en SQLite.

**Puente:** "Y esto es lo que recibe la persona."

### Slide 5 · 1 · Funciona — el libro (45 s)

"El libro llega con portada y dedicatoria, un índice donde cada capítulo es un
enlace, y esta ficha: los personajes y los lugares, cada uno con el capítulo
donde aparece por primera vez.

Esa ficha no la escribe un modelo al final: sale de la **story bible**, la base
de datos donde el sistema guarda cada hecho, cada personaje y en qué capítulo se
usa. Y lo revisé en un navegador real: la versión 2 y la 3 pasan la revisión
visual."

**Puente:** "Y ahora lo más interesante: qué pasa cuando el lector cambia algo."

### Slide 6 · 1 · Funciona — el cambio del lector (1 min 15 s)

"El comprador se da cuenta de que el observatorio que el niño construyó con su
abuelo no era de cartón: era una **casa del árbol**. Lo cambia en la página.

El sistema consulta la story bible, que sabe que ese dato aparece en los
capítulos 3 y 10. **Solo esos dos se reescriben**, y vuelven a pasar por el mismo
control de calidad que el resto.

Sale la versión 3. A la izquierda, su primera página: qué cambió y qué capítulos
se reescribieron. La versión 2 se queda intacta. A la derecha, el capítulo 3
nuevo: ya habla de la casa del árbol.

Costó 10.31 dólares medidos y unos 46 minutos."

**Si hay video, va aquí.**

**Puente:** "Eso es lo que funciona. Segunda razón: por qué es confiable. Y
empieza por una decisión."

### Slide 7 · 2 · Es confiable — la decisión clave (1 min)

"La decisión que sostiene todo: **el escritor nunca puede leer los capítulos
anteriores.**

No es que se lo pida en un prompt: su única herramienta regresa nombres de
archivos, nunca su contenido. Entonces, ¿cómo sabe lo que pasó antes? Por la
story bible y por un resumen corto de lo que ha ocurrido.

¿Por qué importa? Porque así el capítulo 10 pesa lo mismo que el 1: no es más
caro ni más lento, el contexto nunca se llena y nada pasa del límite de 100,000
tokens. Toda la continuidad pasa por la story bible."

**Puente:** "Vamos a ver el recorrido completo de una novela."

### Slide 8 · 2 · Es confiable — el recorrido (1 min 15 s)

"Una novela pasa por siete etapas, siempre en este orden:
0, la entrevista convierte lo que escribe el comprador en un pedido validado;
1, se escriben las reglas del mundo;
2, los personajes y la cronología;
3, el guion capítulo por capítulo, que un auditor revisa antes de escribir nada;
4, diez veces: se escribe cada capítulo y se critica;
5, se unifica la voz;
6, un juez lee el libro completo y se genera el PDF.

Tres piezas lo mantienen en orden:
- el **orquestador**, Claude Code, sigue un procedimiento escrito y llama a cada
  agente en su etapa; él no escribe la novela;
- el **control de calidad**: cada capítulo necesita por lo menos un 8 en seis
  criterios; tiene tres intentos con una hoja de correcciones y, si no pasa, la
  novela se detiene: nunca entra un capítulo malo;
- y **dos hooks**: scripts que corren solos cada vez que se escribe un capítulo,
  para validarlo y para buscar palabras prohibidas.

Como cada etapa deja su resultado guardado, si algo falla se retoma desde ahí."

**Los seis criterios:** continuidad, reglas del mundo, guion, prosa, longitud y
que el modelo no deje comentarios suyos en el texto. Los cuatro primeros los
juzga un modelo; los dos últimos, código.

**Puente:** "¿Quién hace cada cosa? Trece agentes."

### Slide 9 · 2 · Es confiable — los agentes que crean (1 min)

"Son trece agentes y cada uno hace una sola cosa. Siete crean el libro:
- el **entrevistador** convierte lo que escribe el comprador en el pedido y
  pregunta lo que falta; no decide nada;
- el **constructor del mundo** escribe sus reglas;
- el **arquitecto de personajes** escribe el reparto, la cronología y los
  misterios; solo estos dos pueden escribir la story bible;
- el **arquitecto del guion** escribe qué pasa en cada capítulo;
- el **escritor** escribe un capítulo a la vez, sin leer los anteriores;
- el **editor de estilo** unifica la voz, pero no puede cambiar ni una palabra;
- y el **editor** escribe la sinopsis de contraportada; el libro lo arma el
  código.

Todos corren en Haiku, el modelo más barato."

**Puente:** "Y seis lo revisan."

### Slide 10 · 2 · Es confiable — los agentes que revisan (1 min)

"La regla es que **quien escribe no se califica a sí mismo**. Seis agentes
revisan:
- el de **continuidad** compara el capítulo con la story bible;
- el de **reglas del mundo** revisa que se respeten, y además audita el guion
  antes de empezar;
- el de **guion** revisa que el capítulo haga lo que le tocaba, en orden;
- el de **prosa** juzga cómo está escrito: párrafos que no avanzan, diálogos
  genéricos, repeticiones;
- uno opcional hace los tres primeros en una sola lectura, para gastar menos;
- y el **juez** lee el libro completo una vez y lo califica en seis criterios.

Y lo importante: **los críticos solo informan. Quien decide si un capítulo entra
es el código**: toma la calificación más baja y la compara con 8."

**Si preguntan "¿y si el modelo se inventa la calificación?":** "Una respuesta
mal formada no cuenta como aprobada, la decisión es código, y una auditoría la
vuelve a calcular después de cada novela."

**Puente:** "Esos son los agentes. Ahora, los controles."

### Slide 11 · 2 · Es confiable — validación (1 min)

"Tengo cuatro tipos de validadores, y cada uno actúa en un punto fijo:
- **programáticos**, que son código y siempre dan el mismo resultado: el
  formato del pedido, los nombres exactos, la longitud, los hechos obligatorios,
  las palabras prohibidas y la revisión visual;
- **semánticos**, que juzga un modelo o una persona: los críticos, el juez y la
  revisión humana;
- **formal sobre la historia**: Lean revisaría la cronología; no se ejecutó
  porque no se instala sin permisos de administrador, y así lo declaro;
- **formal sobre el sistema**: describí el sistema en TLA+ y el verificador
  revisó 18,253 estados sin errores: nada sin validar se publica, reanudar no
  duplica, la versión anterior se conserva y siempre termina.

El principio: **lo que se puede revisar con un script, se revisa con un
script**; los modelos solo juzgan donde hace falta criterio."

**Puente:** "Y todo esto queda registrado."

### Slide 12 · 2 · Es confiable — formal y observabilidad (1 min)

"Un sistema confiable no es el que nunca falla: es el que **se da cuenta** cuando
falla. Todo queda registrado en SQLite y en Langfuse: cada novela es una sesión,
cada versión una traza y cada validador una calificación.

Y el registro me mostró tres fallas reales, que corregí:
- con el orquestador en el modelo barato, dejó de usar mis agentes y el escritor
  perdió su aislamiento; por eso el orquestador no va en Haiku;
- con un tope de gasto demasiado bajo, cerró una novela sin pasar el control de
  calidad; lo detectó la auditoría y subí el tope;
- y la configuración decía un modelo y corrió otro; lo vi en el registro de
  costos.

Además, la entrevista rechazó un pedido con un recuerdo fechado antes de que la
persona naciera, sin gastar un centavo."

**Puente:** "Por último en esta parte: lo que no debe salir."

### Slide 13 · 2 · Es confiable — guardrails (1 min)

"Cuatro barreras:
- **palabras prohibidas** en tres niveles: para todos, para este cliente y para
  esta novela; da igual mayúsculas, acentos o plural; si aparece una, el capítulo
  regresa al escritor. Resultado: cero apariciones en los tres libros
  publicados;
- **inyección**: el texto libre del comprador nunca es una orden; lo probé con un
  pedido trampa que decía 'ignora tus instrucciones' y no llegó al libro;
- **datos personales**: el modelo nunca ve el nombre real de quien recibe el
  regalo; el código lo pone al publicar, y no hay ninguna clave en el
  repositorio;
- y un **registro de auditoría** de cada decisión."

**Puente:** "Tercera razón: el costo."

### Slide 14 · 3 · Costo conocido — presupuesto (1 min)

"Aquí siempre separo lo **medido** de lo **supuesto**.

Medido: la novela de diez capítulos costó **74.20 dólares**, en 169 minutos. Sale
del propio registro de Claude Code, no de una estimación.

Supuesto, para validar con ustedes: 6 dólares de infraestructura por novela y un
precio de venta de 129. Con eso queda un **margen del 38 %**.

La tabla muestra el margen mensual con 20, 100 y 500 novelas al mes, y qué pasa
si los tokens suben un 50 % o si todos los capítulos necesitan el tercer
intento: en todos los casos sigue habiendo margen."

**Cuenta, por si la piden:** 129 − 74.20 − 6 = 48.80 dólares → 38 %.

**Puente:** "Y lo más útil: en qué se va ese dinero."

### Slide 15 · 3 · Costo conocido — en qué se va (1 min)

"De los 74.20 dólares, **los agentes que escriben y critican son solo el 8 %**:
6.07 dólares. **El 92 % es el orquestador**: 68.13 dólares.

¿Por qué? Porque el orquestador es un modelo que vuelve a leer el procedimiento
en cada turno para decidir cosas que ya son reglas. Abaratar los agentes ya no
mueve la cifra: lo que hay que abaratar es el orquestador.

Ya se nota: en el cambio del lector, con el orquestador en un modelo más barato,
un capítulo costó 4.57 dólares contra los 7.52 de antes."

**Puente:** "Y eso me lleva al siguiente paso, que ya está aprobado."

### Slide 16 · 3 · Costo conocido — siguiente paso (45 s)

"**El código conduce; el modelo solo juzga.** Hoy un modelo decide el ciclo de
cada capítulo: escribir, criticar, reintentar. Con el siguiente paso, ese ciclo
lo ejecuta código en Python: escritor, los cuatro críticos en paralelo,
calificación mínima y reintento. Los agentes son los mismos y la vara no cambia:
8, seis criterios y tres intentos.

Ya está construido y aprobado; falta medirlo en una novela real. Y lo que
descarté: poner el orquestador en el modelo barato, porque ya vi que rompe el
aislamiento del escritor."

**Puente:** "Regreso al principio."

### Slide 17 · En resumen (1 min)

"La respuesta era: storyMaker entrega una novela personalizada de diez
capítulos, revisada y con un costo medido. Y lo acaban de ver:
- **funciona**: una novela real, un 8.33 del juez y un cambio que reescribió
  solo dos capítulos;
- **es confiable**: trece agentes, y quien decide si un capítulo entra es el
  código;
- **sé cuánto cuesta**: 74.20 dólares, el 92 % en el orquestador, y el paso que
  lo reduce ya está listo.

Los riesgos, dichos con claridad: el costo depende del orquestador; el juez es un
modelo y no siempre da la misma calificación; los hechos obligatorios se buscan
por texto literal; y tres capítulos quedaron un poco abajo de las 1,000
palabras.

Además del mínimo hice un servidor MCP de solo lectura, una revisión de
seguridad, un linter de prosa y un segundo modelo TLA+ que encontró una falla
real. Los siguientes pasos: el ciclo en código por defecto, inicio de sesión y
un lector web donde se pueda seleccionar el texto."

### Slide 18 · Gracias (10 s)

"Gracias. Ahora se los muestro en vivo, y después, las preguntas que quieran."

---

## Parte 2 — Demo en vivo (≈ 8 min)

Panel en `http://localhost:5191`, servidor en `:8000`. **Antes de empezar:**
revisa que la biblioteca cargue y que no haya ningún orquestador corriendo.

1. **Biblioteca.** "Esta es la biblioteca: novelas listas, en proceso y
   detenidas."
2. **Abrir *The Other Side of the Hill* → Progress.** "Está lista. Aquí está el
   costo, y si despliego el detalle, la calificación de cada capítulo y cuántos
   intentos necesitó."
3. **Read.**
   - "El libro, con portada, dedicatoria e índice."
   - Da clic en un personaje de la ficha: "y salta al capítulo donde aparece".
   - Cambia entre la versión 1, la 2 y la 3: "todas las versiones se conservan".
   - **Download PDF**: "y se descarga con el título del libro".
4. **Ask for a change.** Elige el hecho del observatorio, escribe "a wooden
   treehouse observatory" y muestra que se reescribirían los capítulos 3 y 10
   **antes de gastar nada**. "Esto ya lo corrí: es la versión 3." Abre su
   página de novedades.
5. **New novel.** Da clic en "Fill this in with the example brief", muestra los
   pasos, la longitud de 1 a 10 y el aviso de datos faltantes. **No des clic en
   Order en vivo**: cuesta dinero real y tarda.
6. **Langfuse.** Una traza de la novela, con sus llamadas y sus calificaciones.

**Si algo falla en vivo:** abre `ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`
o pon el video, que muestra el mismo recorrido.

---

## Parte 3 — Preguntas difíciles, con respuesta corta

| pregunta | respuesta |
|---|---|
| ¿Por qué no un solo modelo que escriba todo el libro? | Porque se contradice, repite y olvida lo que se le pidió, y cada capítulo le cuesta más que el anterior. Separar escritor y críticos, y darles la story bible, lo evita. |
| ¿Cómo sabe el escritor lo que pasó antes? | Por la story bible (hechos, personajes, cronología) y un resumen de lo ocurrido de máximo 260 palabras. Nunca por los capítulos anteriores. |
| ¿Y si el juez o un crítico se equivocan? | Los críticos solo informan; la decisión es código. El juez no bloquea: informa por versión, y lo comparo con mi revisión humana (8.33 contra 8). |
| ¿Por qué 1 capítulo en las evaluaciones? | Cinco novelas completas costaban unos 250 dólares y no daba el tiempo; cada validador se prueba igual con un capítulo. La novela de ejemplo sí tiene 10. Está declarado. |
| ¿Por qué no se ejecutó Lean? | Su instalador necesita permisos de administrador en la máquina, que no tenía. El export está escrito y el motivo, declarado. |
| ¿Por qué hechos obligatorios da 1 de 3? | La revisión busca el texto literal: "tomato plants" no cuenta como "the tomatoes". Prefiero marcar un hecho como no cubierto antes que darlo por bueno sin estarlo. |
| ¿Tres capítulos abajo de 1,000 palabras? | Tienen entre 934 y 967. El control acepta un 10 % de tolerancia; el enunciado pide 1,000. Lo declaro como riesgo. |
| ¿Por qué el orquestador no va en Haiku, si es más barato? | Lo probé: dejó de usar mis agentes y el escritor tuvo acceso a todo. Por eso el ahorro viene de pasar el ciclo a código, no de un modelo más barato. |
| ¿Cómo se protegen los datos personales? | El modelo nunca ve el nombre real: el código lo pone al publicar. Las credenciales salen del entorno y no hay claves en el repositorio. |
| ¿Qué pasa si se cae a la mitad? | Cada etapa deja su resultado guardado; se continúa desde la primera sin terminar, sin repetir lo hecho. |

---

## Acordeón — las cifras de memoria

| qué | cifra |
|---|---|
| capítulos por novela | 10, de 1,000 a 1,500 palabras |
| agentes | 13 (7 crean, 6 revisan), todos en Haiku |
| control de calidad | calificación mínima 8 en 6 criterios, 3 intentos |
| juez / revisión humana | 8.33 / 8 |
| costo de la novela | 74.20 dólares medidos, 169 min, 468 turnos |
| en qué se va | 92 % orquestador (68.13 dólares), 8 % agentes (6.07 dólares) |
| cambio del lector (v3) | capítulos 3 y 10, 10.31 dólares, 46 min |
| margen | 38 % con precio de 129 dólares e infraestructura de 6 (supuestos) |
| tope de gasto | 60 dólares por novela |
| TLA+ | 18,253 estados sin errores |
| palabras prohibidas en los libros | 0 |
