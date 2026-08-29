---
name: memoria-calculo
description: Estándar para producir memorias de cálculo (Word) y sus libros de Excel trazables en estudios hidrológicos e hidráulicos. Úsalo al preparar, estructurar o revisar un entregable de cálculo — balance hídrico, máximas avenidas, diseño de estructuras, socavación, drenaje — o al generar un libro de Excel con Python. Define la arquitectura del libro, la convención de celdas, las reglas de trazabilidad y la estructura de la memoria.
---

# Memoria de cálculo y libro Excel trazable

El criterio que manda sobre todos los demás: **un revisor externo, sin hablar
contigo, tiene que poder reconstruir de dónde sale cada número.** Si un valor no
se puede rastrear hasta un dato de entrada o una fuente citada, el entregable no
está terminado, por correcto que sea el resultado.

Este estándar es la línea base. Es normal ajustarlo por proyecto; lo que no se
ajusta son las reglas de trazabilidad de la sección correspondiente.

## Arquitectura del libro Excel

Una hoja por función, numeradas para que el orden sea el del cálculo:

| Hoja | Contenido |
|---|---|
| `00_Control` | Proyecto, cliente, estructura calculada, autor, revisor, fecha, versión, y un registro de cambios de una línea por revisión. |
| `01_Datos` | Datos de entrada crudos, tal como llegaron de la fuente. **No se calcula nada aquí.** Series, coordenadas, áreas, cotas, datos de campo. |
| `02_Parametros` | Todo coeficiente, factor y criterio de diseño, uno por fila, con su fuente. Ver abajo. |
| `03_…`, `04_…` | Las etapas del cálculo, una hoja por etapa, en el orden en que se ejecutan. |
| `98_Resultados` | Los valores que salen a la memoria y a los planos, y nada más. Todos por referencia a las hojas de cálculo, ninguno tecleado. |
| `99_Verificacion` | Comprobaciones automáticas: cierre de balance, coherencia de unidades, rangos esperados. Cada una devuelve OK o el error numérico, no un texto libre. |

### La hoja `02_Parametros` es el corazón del libro

Una fila por parámetro, con estas columnas fijas:

`Símbolo | Descripción | Valor | Unidad | Fuente | Observación`

- **Fuente** es obligatoria y específica: norma y artículo, manual y tabla, ensayo,
  dato de campo, o calibración. `"ANA"` o `"manual de hidrología"` a secas no es
  una fuente. Si el valor es un supuesto, la fuente dice **"supuesto"** y la
  observación explica en qué se apoya.
- Un parámetro sin fuente verificable es un entregable bloqueado, no un detalle
  pendiente. No lo rellenes con un valor plausible.
- Cada fila lleva un **nombre definido** de Excel (`n_manning`, `Tr_diseno`,
  `C_escorrentia`). Las fórmulas usan el nombre, no la referencia de celda: se
  leen solas y sobreviven a que alguien inserte una fila.

### Convención de color de celda

Esta convención es lo que permite auditar una hoja de un vistazo:

- **Azul** — dato de entrada, editable.
- **Negro** — fórmula calculada en esta misma hoja.
- **Verde** — referencia a otra hoja del mismo libro.
- **Rojo** — valor pendiente de confirmar o referencia a un archivo externo.
  Ningún entregable sale con celdas rojas.

## Reglas de trazabilidad

1. **Fórmulas vivas, nunca valores pegados.** Si un número se calculó, en la
   celda va la fórmula. Pegar el resultado de un cálculo hecho aparte rompe la
   auditoría y es el error más común.
2. **Ninguna constante escrita dentro de una fórmula.** Nada de
   `=0.0195*L^0.77...` con los coeficientes embebidos: cada uno vive en
   `02_Parametros` y la fórmula lo referencia por su nombre. La única excepción
   son las constantes de la propia formulación matemática, que van acompañadas
   de la cita del método.
3. **Unidades declaradas en cada columna y cada parámetro**, y coherentes en toda
   la cadena. Cuando una fórmula incluye un factor de conversión, ese factor es
   una fila con nombre en `02_Parametros`, no un número suelto.
4. **Cada resultado que aparece en la memoria vive en `98_Resultados`** y desde
   ahí se referencia. Un número que existe en el Word pero no en el libro no
   tiene procedencia.
5. **Nada se sobreescribe en `01_Datos`.** Si una serie se completó, se corrigió
   o se filtró, eso ocurre en una hoja de proceso, con el dato original intacto y
   el criterio documentado.
6. **El origen de los datos queda etiquetado**: estación y periodo de registro
   para dato observado; producto y versión para grillado o reanálisis; y si un
   grillado alimenta un caudal de diseño, la observación dice si hubo validación
   o corrección de sesgo, o declara que no la hubo.
7. **El sistema de coordenadas se lee del dato y se escribe en `00_Control`.**
   Nunca se asume por la zona del proyecto.

## Estructura de la memoria (Word)

1. **Generalidades** — antecedentes, objetivo, alcance, ubicación.
2. **Información básica** — cartografía y topografía empleada, información
   hidrometeorológica con estación, periodo y tipo de dato, información de campo.
   Aquí se declara qué información existe y cuál falta.
3. **Criterios y normativa aplicada** — qué norma o manual rige cada criterio,
   citado de forma específica. Si un criterio se toma de normativa internacional
   porque la peruana no cubre el caso, se dice explícitamente y se justifica.
4. **Caracterización del área de estudio** — cuenca, parámetros geomorfológicos,
   cobertura, y lo que condicione el cálculo.
5. **Metodología** — el método elegido y **por qué** ese y no otro, con sus
   condiciones de aplicabilidad y sus límites.
6. **Cálculo y resultados** — el desarrollo, con las tablas que salen del libro.
7. **Verificación** — el criterio de aceptación y el resultado frente a él
   (error de cierre, indicadores de calibración, rangos de contraste).
8. **Conclusiones y recomendaciones** — separando lo que el cálculo sostiene de
   lo que queda como recomendación.
9. **Referencias** y **anexos** — el libro de Excel es un anexo, no un archivo
   suelto que se envía por correo.

Reglas de redacción:

- Toda cifra en el texto lleva unidad, y su procedencia es rastreable a la tabla
  o celda que la produjo.
- Los supuestos van en el cuerpo del documento, no escondidos en una nota al pie.
- Se distingue siempre lo calculado de lo estimado y de lo asumido.
- No se escribe un valor normativo de memoria: se verifica contra la fuente antes
  de ponerlo.

## Al generar el libro con Python

Usa `openpyxl` y `scripts/generar_libro.py` de esta skill como punto de partida.
Tres cosas que rompen el entregable si se pasan por alto:

- **Escribe fórmulas, no resultados.** `ws["D5"] = "=C5*n_manning"`, no el número
  que calculaste en Python. Si necesitas el valor para verificar, calcúlalo
  aparte y compáralo; no lo pegues en la celda.
- **openpyxl no evalúa fórmulas.** El archivo que genera no tiene valores
  cacheados hasta que Excel lo abre y guarda. Por eso releer con
  `data_only=True` un libro recién generado devuelve `None`: no es un error del
  script. Si otro proceso necesita los números, o abres el libro primero, o
  calculas en Python en paralelo.
- **Las fórmulas se escriben en inglés y con coma** (`=SUM(A1:A5)`), aunque tu
  Excel esté en español y use punto y coma. Excel las traduce al abrir. Escribir
  `=SUMA(A1;A5)` produce un archivo corrupto.

## Antes de entregar

- [ ] No queda ninguna celda roja ni ningún parámetro sin fuente.
- [ ] `99_Verificacion` pasa, y el criterio de aceptación está escrito, no
      sobreentendido.
- [ ] Ninguna constante quedó embebida en una fórmula.
- [ ] Las unidades son coherentes de extremo a extremo.
- [ ] El CRS está declarado y se leyó del dato.
- [ ] Cada cifra de la memoria existe en `98_Resultados`.
- [ ] Pasó por el subagente **verificador** con contexto limpio.
