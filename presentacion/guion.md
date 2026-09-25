# Guion: lo que tengo que decir

Para el deck de 19 slides. Una sola persona presenta.

## Slide 1 · Portada

Buenos días. Les presento storyMaker, de Qaracter: novelas personalizadas para regalar, escritas por un sistema de agentes que se revisa a sí mismo. Empiezo por la conclusión.

## Slide 2 · La respuesta

Les traigo una respuesta y tres razones.

La respuesta: storyMaker entrega una novela personalizada de diez capítulos, revisada y con un costo medido.

Primera razón: funciona. Hay una página web donde se pide, se lee y se corrige, y una novela de ejemplo real: diez capítulos, un juez automático le dio 8.33 sobre 10 y mi revisión humana, un 8. Cuando el lector cambió un dato, solo se reescribieron los dos capítulos que lo usaban.

Segunda: es confiable. Todo lo que el sistema promete lo revisa alguien que no lo escribió. Hay trece agentes con una tarea cada uno, y ningún capítulo entra al libro sin sacar por lo menos un 8 en seis criterios.

Tercera: sé cuánto cuesta. 74.20 dólares medidos por novela, y sé exactamente en qué se va el dinero y cómo bajarlo.

El resto de la presentación demuestra cada una de las tres, en este orden. Antes, treinta segundos sobre lo que pide el cliente.

## Slide 3 · El cliente

Páginas de Regalo vende regalos. Quien compra es un papá, una pareja, un hijo o un compañero de trabajo, y quiere que la persona que lo recibe se reconozca: su nombre, sus recuerdos, sus manías. Y que el libro se lea de principio a fin sin tropezar: sin un personaje que cambia de carácter, sin saltos de tiempo, sin un final cortado.

En concreto: diez capítulos de entre 1,000 y 1,500 palabras, en PDF, y poder corregir un dato después.

Primera razón: funciona. Se los muestro.

## Slide 4 · La web

Esta es la página web, funcionando. Arriba, el estado en una frase: cuántas novelas se están escribiendo, cuántas están listas y cuántas se detuvieron. Abajo, una tarjeta por novela.

Desde aquí el comprador hace cuatro cosas. Pedir: "Order a new novel" abre la entrevista con los datos, los recuerdos, el tono, las palabras prohibidas y los hechos que tienen que aparecer. Seguir: cada tarjeta dice si la novela se está escribiendo, si está lista o si se detuvo, y en qué punto. Leer y corregir: "Open" muestra el libro, lo descarga en PDF y permite pedir un cambio. Y si una novela se detuvo, continuarla desde donde se quedó, sin empezar de cero, o mandarla a la papelera.

La primera tarjeta es mi novela de ejemplo, lista para leer. Y esto es lo que recibe la persona.

## Slide 5 · El libro

El libro llega con portada y dedicatoria, un índice donde cada capítulo es un enlace, y esta ficha: los personajes y los lugares, cada uno con el capítulo donde aparece por primera vez.

Esa ficha no la escribe un modelo al final: sale de la story bible, la base de datos donde el sistema guarda cada hecho, cada personaje y en qué capítulo se usa. Y lo revisé en un navegador real: la versión 2 y la 3 pasan la revisión visual.

Y ahora lo más interesante: qué pasa cuando el lector cambia algo.

## Slide 6 · El cambio del lector

El comprador se da cuenta de que el observatorio que el niño construyó con su abuelo no era de cartón: era una casa del árbol. Lo cambia en la página.

El sistema consulta la story bible, que sabe que ese dato aparece en los capítulos 3 y 10. Solo esos dos se reescriben, y vuelven a pasar por el mismo control de calidad que el resto.

Sale la versión 3. A la izquierda, su primera página: qué cambió y qué capítulos se reescribieron. La versión 2 se queda intacta. A la derecha, el capítulo 3 nuevo: ya habla de la casa del árbol.

Costó 10.31 dólares medidos y unos 46 minutos.

Eso es lo que funciona. Segunda razón: por qué es confiable. Y empieza por una decisión.

## Slide 7 · La decisión clave

La decisión que sostiene todo: el escritor nunca puede leer los capítulos anteriores.

No es que se lo pida en un prompt: su única herramienta regresa nombres de archivos, nunca su contenido. Entonces, ¿cómo sabe lo que pasó antes? Por la story bible y por un resumen corto de lo que ha ocurrido.

¿Por qué importa? Porque así el capítulo 10 pesa lo mismo que el 1: no es más caro ni más lento, el contexto nunca se llena y nada pasa del límite de 100,000 tokens. Toda la continuidad pasa por la story bible.

Vamos a ver el recorrido completo de una novela.

## Slide 8 · El recorrido

Una novela pasa por siete etapas, siempre en este orden. Cero: la entrevista convierte lo que escribe el comprador en un pedido validado. Uno: se escriben las reglas del mundo. Dos: los personajes y la cronología. Tres: el guion capítulo por capítulo, que un auditor revisa antes de escribir nada. Cuatro, diez veces: se escribe cada capítulo y se critica. Cinco: se unifica la voz. Seis: un juez lee el libro completo y se genera el PDF.

Tres piezas lo mantienen en orden. El orquestador, Claude Code, sigue un procedimiento escrito y llama a cada agente en su etapa; él no escribe la novela. El control de calidad: cada capítulo necesita por lo menos un 8 en seis criterios; tiene tres intentos con una hoja de correcciones y, si no pasa, la novela se detiene: nunca entra un capítulo malo. Y dos hooks: scripts que corren solos cada vez que se escribe un capítulo, para validarlo y para buscar palabras prohibidas.

Como cada etapa deja su resultado guardado, si algo falla se retoma desde ahí.

¿Quién hace cada cosa? Trece agentes.

## Slide 9 · Los agentes que crean

Son trece agentes y cada uno hace una sola cosa. Siete crean el libro.

El entrevistador convierte lo que escribe el comprador en el pedido y pregunta lo que falta; no decide nada. El constructor del mundo escribe sus reglas. El arquitecto de personajes escribe el reparto, la cronología y los misterios; solo estos dos pueden escribir la story bible. El arquitecto del guion escribe qué pasa en cada capítulo. El escritor escribe un capítulo a la vez, sin leer los anteriores. El editor de estilo unifica la voz, pero no puede cambiar ni una palabra. Y el editor escribe la sinopsis de contraportada; el libro lo arma el código.

Todos corren en Haiku, el modelo más barato. Y seis lo revisan.

## Slide 10 · Los agentes que revisan

La regla es que quien escribe no se califica a sí mismo. Seis agentes revisan.

El de continuidad compara el capítulo con la story bible. El de reglas del mundo revisa que se respeten, y además audita el guion antes de empezar. El de guion revisa que el capítulo haga lo que le tocaba, en orden. El de prosa juzga cómo está escrito: párrafos que no avanzan, diálogos genéricos, repeticiones. Uno opcional hace los tres primeros en una sola lectura, para gastar menos. Y el juez lee el libro completo una vez y lo califica en seis criterios.

Y lo importante: los críticos solo informan. Quien decide si un capítulo entra es el código: toma la calificación más baja y la compara con 8.

Esos son los agentes. Ahora, los controles.

## Slide 11 · Validación

Tengo cuatro tipos de validadores, y cada uno actúa en un punto fijo.

Los programáticos, que son código y siempre dan el mismo resultado: el formato del pedido, los nombres exactos, la longitud, los hechos obligatorios, las palabras prohibidas y la revisión visual.

Los semánticos, que juzga un modelo o una persona: los críticos, el juez y la revisión humana.

El formal sobre la historia: Lean revisaría la cronología; no se ejecutó porque no se instala sin permisos de administrador, y así lo declaro.

Y el formal sobre el sistema: describí el sistema en TLA+ y el verificador revisó 18,253 estados sin errores: nada sin validar se publica, reanudar no duplica, la versión anterior se conserva y siempre termina.

El principio: lo que se puede revisar con un script, se revisa con un script; los modelos solo juzgan donde hace falta criterio.

Y todo esto queda registrado.

## Slide 12 · Observabilidad

Un sistema confiable no es el que nunca falla: es el que se da cuenta cuando falla. Todo queda registrado en SQLite y en Langfuse.

Y el registro me mostró tres fallas reales, que corregí. Con el orquestador en el modelo barato, dejó de usar mis agentes y el escritor perdió su aislamiento; por eso el orquestador no va en Haiku. Con un tope de gasto demasiado bajo, cerró una novela sin pasar el control de calidad; lo detectó la auditoría y subí el tope. Y la configuración decía un modelo y corrió otro; lo vi en el registro de costos.

Además, la entrevista rechazó un pedido con un recuerdo fechado antes de que la persona naciera, sin gastar un centavo.

Así se ve ese registro.

## Slide 13 · Langfuse

Este es Langfuse, la herramienta donde queda registrado todo. Cada novela es una sesión y cada versión del libro es una traza.

Aquí se ve cada llamada: la del orquestador y la de cada agente, con su nombre y el capítulo que trabajó; por ejemplo, el escritor del capítulo 9 o el crítico de prosa del capítulo 9. De cada una guardo la entrada, la salida y lo que costó.

Y cada validador manda su calificación: la novela de ejemplo tiene 125.

Por último en esta parte: lo que no debe salir.

## Slide 14 · Guardrails

Hay cuatro barreras.

Palabras prohibidas, en tres niveles: para todos, para este cliente y para esta novela. Da igual mayúsculas, acentos o plural: si aparece una, el capítulo regresa al escritor. Resultado: cero apariciones en los tres libros publicados.

Inyección: el texto libre del comprador nunca es una orden. Lo probé con un pedido trampa que decía "ignora tus instrucciones", y no llegó al libro.

Datos personales: el modelo nunca ve el nombre real de quien recibe el regalo; el código lo pone al publicar, y no hay ninguna clave en el repositorio.

Y un registro de auditoría de cada decisión.

Tercera razón: el costo.

## Slide 15 · Presupuesto

Aquí siempre separo lo medido de lo supuesto.

Medido: la novela de diez capítulos costó 74.20 dólares, en 169 minutos. Sale del propio registro de Claude Code, no de una estimación.

Supuesto, para validar con ustedes: 6 dólares de infraestructura por novela y un precio de venta de 129. Con eso queda un margen del 38 %.

La tabla muestra el margen mensual con 20, 100 y 500 novelas al mes, y qué pasa si los tokens suben un 50 % o si todos los capítulos necesitan el tercer intento: en todos los casos sigue habiendo margen.

Y lo más útil: en qué se va ese dinero.

## Slide 16 · En qué se va el dinero

De los 74.20 dólares, los agentes que escriben y critican son solo el 8 %: 6.07 dólares. El 92 % es el orquestador: 68.13 dólares.

¿Por qué? Porque el orquestador es un modelo que vuelve a leer el procedimiento en cada turno para decidir cosas que ya son reglas. Abaratar los agentes ya no mueve la cifra: lo que hay que abaratar es el orquestador.

Ya se nota: en el cambio del lector, con el orquestador en un modelo más barato, un capítulo costó 4.57 dólares contra los 7.52 de antes.

Y eso me lleva al siguiente paso, que ya está aprobado.

## Slide 17 · Siguiente paso

El código conduce; el modelo solo juzga. Hoy un modelo decide el ciclo de cada capítulo: escribir, criticar, reintentar. Con el siguiente paso, ese ciclo lo ejecuta código en Python: escritor, los cuatro críticos en paralelo, calificación mínima y reintento. Los agentes son los mismos y la vara no cambia: 8, seis criterios y tres intentos.

Ya está construido y aprobado; falta medirlo en una novela real. Y lo que descarté: poner el orquestador en el modelo barato, porque ya vi que rompe el aislamiento del escritor.

Regreso al principio.

## Slide 18 · En resumen

La respuesta era: storyMaker entrega una novela personalizada de diez capítulos, revisada y con un costo medido. Y lo acaban de ver.

Funciona: una novela real, un 8.33 del juez y un cambio que reescribió solo dos capítulos.

Es confiable: trece agentes, y quien decide si un capítulo entra es el código.

Sé cuánto cuesta: 74.20 dólares, el 92 % en el orquestador, y el paso que lo reduce ya está listo.

Los riesgos, dichos con claridad: el costo depende del orquestador; el juez es un modelo y no siempre da la misma calificación; los hechos obligatorios se buscan por texto literal; y tres capítulos quedaron un poco abajo de las 1,000 palabras.

Los siguientes pasos: el ciclo en código por defecto, inicio de sesión y un lector web donde se pueda seleccionar el texto.

## Slide 19 · Gracias

Gracias. Ahora se los muestro en vivo, y después, las preguntas que quieran.

---

## Demo en vivo

Esta es la biblioteca: novelas listas, en proceso y detenidas.

Esta es mi novela de ejemplo. Está lista. Aquí está el costo, y si despliego el detalle, la calificación de cada capítulo y cuántos intentos necesitó.

Este es el libro, con portada, dedicatoria e índice. Si doy clic en un personaje de la ficha, salta al capítulo donde aparece. Aquí puedo cambiar entre la versión 1, la 2 y la 3: todas las versiones se conservan. Y se descarga en PDF con el título del libro.

Ahora, pedir un cambio. Elijo el dato del observatorio y escribo el nuevo. Antes de gastar nada, el sistema me dice qué capítulos se reescribirían: el 3 y el 10. Esto ya lo corrí: es la versión 3, y abre con su página de novedades.

Así se pide una novela nueva: estos son los pasos, aquí se elige la longitud de 1 a 10, y aquí avisa si falta algún dato. No lo voy a enviar en vivo porque cuesta dinero real y tarda.

Y aquí, en Langfuse, está el registro de la novela, con todas sus llamadas y sus calificaciones.
