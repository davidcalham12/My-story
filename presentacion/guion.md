# Guion — presentación al cliente y demo en directo

**Mañana, 25-09-2026.** Primero la presentación: es para un cliente, así que
va **resumen primero y puntos clave en detalle después**. Después, la
herramienta **en directo**. Entrega: vídeo, código y presentación.

El deck es el artifact *storyMaker — Qaracter proposal*, con 13 slides y la
identidad Qaracter design FRM. Aquí va lo que se dice en cada slide y la
evidencia que lo respalda. Cada cifra lleva su procedencia; lo que no está
medido dice **supuesto** o **estimado**.

Actualizado: 2026-09-24, 18:50 UTC, con la novela de 10 capítulos terminada.

---

## Parte 1 — Presentación (unos 12 minutos)

### 1. Portada
Qaracter presenta a un cliente ficticio (*Páginas de Regalo S.L.*):
*storyMaker, novelas personalizadas para regalar*.

### 2. Resumen: la slide que hay que dejar clara
Cuatro puntos, uno por tarjeta:
1. **Qué hace.** Una entrevista de diez minutos se convierte en una novela de
   hasta 10 capítulos, que se lee en línea o en PDF. Un cambio reescribe solo
   los capítulos afectados.
2. **Calidad comprobada.** Cada capítulo supera seis criterios con nota mínima
   de 8. En la novela de ejemplo, 8 de 10 capítulos se corrigieron solos antes
   de aprobar (medido).
3. **Seguro por diseño.**
   - Resultado: la inyección del brief 04 no llegó al libro, y hay 0 palabras
     prohibidas.
   - Por qué: el texto del comprador nunca es una orden, y el modelo nunca ve el
     nombre del destinatario, que lo pone el código al publicar.
4. **Coste bajo control.** Novela de 10 capítulos: **74,20 USD medidos**, por
   debajo de su techo.

### 3. Problema y cliente
Las plantillas cambian el nombre y poco más. Un modelo solo se contradice,
repite frases y olvida lo que se le pidió.

### 4. Configuración y lectura
- Entrevista → brief validado. Lo que falta o se contradice lo decide el
  código.
- El comprador elige de 1 a 10 capítulos.
- El libro se lee en línea o se descarga en PDF con el título del libro.
- La ficha de personajes y lugares enlaza con cada capítulo.

### 5–6. Arquitectura: la idea central
- **El escritor nunca puede leer los capítulos anteriores.** No es una
  instrucción, es una capacidad: su única herramienta devuelve rutas, nunca
  contenido.
- Doce agentes, un orquestador, la Story Bible en SQLite y la puerta de
  calidad.

### 7. Validadores
- Programáticos: schema, nombres, longitud, hechos, palabras prohibidas y
  revisión visual.
- Semánticos: seis características y el juez con rúbrica.
- Formales: TLA+ y Lean.
- Humano: revisión del dueño.

### 8. Evals, con números (`evals/results.md`, tabla de validaciones)
- 01 y 04 pasan. 03 y 05 se rechazan en la entrevista **sin gastar nada**: 05
  por un recuerdo de 1983 en alguien nacido en 1986. 02 no se generó, por
  presupuesto (declarado).
- **Juez sobre la novela completa: media 8,33** (continuidad 8, tono 9, arco 8,
  coherencia de personajes 9, ritmo 8, personalización natural 8), cada nota
  con su justificación (medido).
- Hechos obligatorios: 1 de 3, porque la comprobación es literal ("tomato
  plants" frente a "the tomatoes"). Es un límite declarado.

### 9. Formal y observabilidad
- TLA+ con TLC: 18.253 estados, sin errores.
- Lean no se ejecutó (elan necesita permisos de administrador), y se declara.
- Langfuse: una traza por novela, spans por agente y 100 scores.
- El registro delató dos desobediencias reales del orquestador.

### 10. Guardrails
Palabras prohibidas en tres niveles, inyección, datos personales (el nombre lo
pone el código) y audit log.

### 11. Presupuesto

| concepto | cifra | procedencia |
|---|---|---|
| novela de ejemplo, 10 capítulos (468 turnos, 169 min) | **74,20 USD** | medido: 53,17 + 21,03 |
| muestra de 1 capítulo (eval 04) | 25,80 USD | medido |
| juez sobre una versión | 2 min | medido; coste no registrado (declarado) |
| infraestructura por novela | 6 USD | **supuesto** |
| precio de venta | 129 USD | **supuesto**, a validar con el cliente |
| margen por novela | 38 % | calculado sobre los supuestos |
| desarrollo | ~54 h × 50 USD/h ≈ 2.700 USD | **supuesto** |

**Mensaje:** un techo por debajo de lo que cuesta el trabajo no ahorra, compra
un libro roto (red-team, caso 10). Ya está construida la palanca para bajar el
coste: el orquestador en Sonnet (aplicado el 24-09) y el bucle del capítulo en
código (SPEC-EXAM-006, aprobado). Los agentes son el 8 % del coste medido; el
92 % es el orquestador (slide "Dónde se va el dinero").

### 12. Demo y riesgos
El cambio del lector ("el observatorio de cartón pasa a ser una casa del
árbol", hecho 36, capítulos 3 y 10 → v3, 10,31 $ medidos) y los riesgos declarados:
- el coste depende del orquestador;
- el juez no es reproducible;
- los hechos se comprueban por texto, no por significado.

### 13. Contraportada

---

## Parte 2 — Demo en directo (unos 8 minutos)

Panel en `http://localhost:5191`, con el servidor en `:8000`. **Antes de
empezar,** comprueba que no hay ningún orquestador vivo y que la biblioteca
carga.

1. **Biblioteca.** Arriba, el resumen: listos, en curso y parados. Las
   tarjetas llevan el título del libro, sin guiones.
2. **Abrir *The Other Side of the Hill*** → *Progress*: "Your novel is ready",
   el coste y el detalle técnico plegado. Despliégalo y enseña la puerta de
   calidad: notas por capítulo e intentos.
3. **Read:**
   - el libro dentro de la página, con portada, dedicatoria e índice;
   - pulsa "chapter 9" en la ficha y salta al capítulo;
   - elige la versión 1 (8 capítulos) y luego la 2 (10): las dos siguen ahí;
   - **Download PDF** baja el archivo con el título del libro.
4. **Ask for a change:** elige el hecho 36 (el observatorio de cartón), escribe
   "a wooden treehouse observatory" y enseña qué capítulos se reescribirían
   (3 y 10) **antes de gastar nada**. Luego abre la v3 ya generada y enseña su
   página de novedades.
5. **New novel:**
   - pulsa "Fill this in with the example brief";
   - enseña los pasos, la longitud de 1 a 10 y la comprobación de lo que falta;
   - **no pulses Order en directo**, porque cuesta dinero de verdad y tarda.
6. **Langfuse:** una traza de la novela, con sus spans y sus scores.

**Si algo falla en directo:** el PDF está en `ejemplos/novela-ejemplo.pdf`,
y el vídeo muestra el recorrido completo.

---

## Entrega
- **Código:** https://github.com/davidcalham12/StoryMaker (rama `main`).
- **Presentación:** el deck (compártelo desde su menú Share).
- **Vídeo:** el recorrido de la Parte 2, grabado por el dueño.
