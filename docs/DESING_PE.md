# Guía de diseño y frontend --- Proyecto agrícola NASA Space Apps

> **Documento de cumplimiento obligatorio para cualquier agente de IA o
> desarrollador que diseñe, genere o modifique la interfaz.**\
> Este archivo define el lenguaje visual, la paleta autorizada, el
> comportamiento de las animaciones y los límites de implementación. Si
> una decisión no está especificada aquí, no debe inventarse como si
> fuera un requisito: se debe conservar el patrón existente o solicitar
> aclaración.

------------------------------------------------------------------------

## 1. Objetivo visual

Construir una interfaz web para un proyecto relacionado con agricultura,
observación de la Tierra y datos geoespaciales. La experiencia debe
sentirse:

-   **Exploratoria y contemplativa**, tomando como referencia la
    sensación de descubrimiento, navegación y observación del entorno de
    *Outer Wilds*.
-   **Cálida, rural y cercana**, tomando como referencia la vida
    agrícola, los ciclos naturales y la claridad visual de *Stardew
    Valley*.
-   **Científica y funcional**, porque se mostrarán datos, mapas,
    indicadores, anomalías y resultados que deben poder interpretarse
    correctamente.
-   **Artesanal, no prefabricada**: debe parecer una interfaz diseñada
    para este proyecto, no una plantilla genérica producida por IA.

Las referencias son de **dirección artística y sensación**, no una
autorización para copiar interfaces, ilustraciones, personajes,
logotipos, música, mapas, iconografía distintiva ni recursos protegidos
de esos juegos.

### Principio rector

La interfaz debe combinar **exploración + naturaleza + lectura
científica de datos**. La ambientación nunca debe perjudicar la
legibilidad, la precisión de los datos ni la facilidad de uso.

------------------------------------------------------------------------

## 2. Paleta cromática autorizada

### 2.1 Colores base

Estos siete colores son la paleta principal definida por el equipo.
Deben centralizarse como tokens y reutilizarse. **No crear colores base
adicionales ni reemplazarlos por colores de moda, colores automáticos de
frameworks o paletas generadas por IA.**

  -----------------------------------------------------------------------
  Token                   Color                   Uso
  ----------------------- ----------------------- -----------------------
  `--color-background`    `#0B1026`               Fondo general de la
                                                  aplicación y áreas de
                                                  mayor profundidad.

  `--color-panel`         `#121A3A`               Paneles, superficies,
                                                  navegación y
                                                  contenedores
                                                  principales.

  `--color-border`        `#1E2A52`               Bordes, separadores,
                                                  límites de paneles y
                                                  divisiones discretas.

  `--color-text-muted`    `#8C9BC4`               Texto secundario,
                                                  etiquetas, ayudas,
                                                  metadatos y estados no
                                                  prioritarios.

  `--color-text`          `#F2E8D5`               Texto principal,
                                                  títulos, valores
                                                  importantes y contenido
                                                  de lectura.

  `--color-turquoise`     `#4FC1B6`               Datos relacionados con
                                                  agua, humedad,
                                                  cantidad, vegetación y
                                                  señales ambientales
                                                  positivas o neutras
                                                  según el contexto.

  `--color-fire`          `#F2A541`               Acento cálido para
                                                  anomalías, selección,
                                                  énfasis puntual y una
                                                  serie de datos
                                                  destacada.
  -----------------------------------------------------------------------

### 2.2 Tokens CSS obligatorios

Definir los colores en un único lugar. No repetir códigos hexadecimales
arbitrariamente en cada componente.

``` css
:root {
  --color-background: #0B1026;
  --color-panel: #121A3A;
  --color-border: #1E2A52;
  --color-text-muted: #8C9BC4;
  --color-text: #F2E8D5;
  --color-turquoise: #4FC1B6;
  --color-fire: #F2A541;
}
```

Si el proyecto ya cuenta con un sistema de variables, adaptar estos
nombres a su convención sin duplicar tokens ni crear una segunda paleta.

### 2.3 Colores semánticos que ya aparecen en la referencia

La imagen de referencia también muestra colores específicos para
clasificar niveles de riesgo y una cuarta categoría. Se consideran
**colores semánticos predefinidos de esa visualización**, no una
invitación a ampliar la paleta general.

  ------------------------------------------------------------------------
  Token sugerido           Muestra de referencia   Uso exclusivo
  ------------------------ ----------------------- -----------------------
  `--risk-low`             `#D7BF8D`               Riesgo bajo.

  `--risk-medium`          `#F2A541`               Riesgo medio.

  `--risk-high`            `#DF6F3D`               Riesgo alto.

  `--risk-category-four`   `#A89AE7`               Cuarta categoría,
                                                   únicamente si el
                                                   dominio realmente la
                                                   necesita.
  ------------------------------------------------------------------------

Los valores anteriores se han estimado visualmente a partir de la
captura proporcionada. Si el equipo dispone de los valores originales
del diseño, esos valores originales tienen prioridad.

**No utilizar estos colores semánticos para decorar botones, fondos
generales, tarjetas, textos o elementos que no representen esos
estados.** No crear otros colores de riesgo sin una decisión explícita
del equipo.

### 2.4 Gradientes de datos permitidos

La referencia utiliza gradientes únicamente para comunicar una escala
continua. Se permiten gradientes de datos derivados de la paleta
existente:

-   **Cantidad (lluvia/humedad):** progresión de valores bajos a altos
    usando tonos derivados del azul oscuro y el turquesa.
-   **Vegetación (NDVI):** progresión de suelo desnudo a vegetación
    densa usando tonos derivados del texto cálido, turquesa y azul
    verdoso.
-   **Anomalía:** progresión de más fresco/húmedo a normal y más
    caliente/seco, usando tonos derivados de los colores base y del
    acento cálido.

Reglas:

1.  Un gradiente debe representar una escala real y tener extremos y
    significado identificables.
2.  No usar gradientes como decoración de fondos, encabezados, botones o
    tarjetas.
3.  No introducir colores saturados nuevos para hacer el gradiente más
    llamativo.
4.  La leyenda debe explicar qué representa cada extremo y, cuando
    corresponda, qué significa el punto medio.
5.  No invertir el significado de una escala sin actualizar su leyenda.
6.  Los valores y colores deben conservar una relación consistente en
    todas las pantallas.

------------------------------------------------------------------------

## 3. Reglas estrictas de color

-   El fondo principal debe permanecer oscuro: `#0B1026`.
-   Las superficies principales deben utilizar `#121A3A`.
-   Los bordes deben ser discretos y utilizar `#1E2A52`.
-   El texto principal debe utilizar `#F2E8D5`.
-   El texto secundario debe utilizar `#8C9BC4`.
-   El turquesa debe comunicar información ambiental o interacción
    relevante, no convertirse en el color de todos los elementos.
-   El naranja debe reservarse para énfasis, anomalías y elementos
    destacados. No pintar toda la interfaz de naranja.
-   No usar blanco puro (`#FFFFFF`) ni negro puro (`#000000`) como
    sustitutos de los colores establecidos.
-   No introducir morado, rosa, azul eléctrico, verde lima, rojo puro u
    otros tonos por iniciativa propia.
-   No añadir colores porque una librería, plantilla o componente los
    incluya por defecto.
-   No cambiar la paleta para "modernizar", "mejorar el contraste
    visual" o "hacerlo más atractivo" sin autorización.
-   Los estados deben identificarse por texto, iconografía o patrones
    además del color. El color por sí solo no debe ser la única señal.

------------------------------------------------------------------------

## 4. Lenguaje visual y composición

### 4.1 Apariencia general

-   Interfaz oscura, sobria y atmosférica.
-   Sensación de herramienta de exploración científica en un entorno
    natural.
-   Composición limpia, con jerarquía visual clara.
-   Espacios suficientes para separar controles, mapas, leyendas y
    datos.
-   Contenedores rectos o con radios moderados y consistentes.
-   Bordes finos y visibles solo cuando ayuden a separar regiones.
-   Los paneles deben tener una función real; no envolver cada texto en
    una tarjeta.
-   Los elementos importantes deben destacar por posición, jerarquía,
    contraste y contexto, no por sombras exageradas.

### 4.2 Inspiración de Outer Wilds

Tomar como referencia conceptual:

-   Exploración de un territorio desconocido.
-   Curiosidad y descubrimiento progresivo.
-   Sensación de escala, orientación y observación.
-   Uso moderado de detalles astronómicos o cartográficos cuando tengan
    sentido para el proyecto.
-   Transiciones que acompañen el desplazamiento o el descubrimiento de
    información.

No convertir la web en una interfaz espacial genérica. El proyecto es
agrícola y terrestre: la navegación, el suelo, el agua, los cultivos, el
clima y la observación satelital deben seguir siendo el centro.

### 4.3 Inspiración de Stardew Valley

Tomar como referencia conceptual:

-   Calidez visual y cercanía con el mundo agrícola.
-   Relación con las estaciones, los cultivos, el clima y los ciclos
    naturales.
-   Detalles gráficos pequeños y deliberados.
-   Sensación de herramienta hecha para una comunidad, no para una
    corporación ficticia.
-   Posibles acentos de pixel art en elementos secundarios, siempre que
    no dificulten la lectura.

No convertir toda la aplicación en pixel art. No usar tipografías
pixeladas para párrafos, tablas, formularios ni valores científicos. No
copiar sprites, personajes, iconos, escenarios ni recursos originales
del juego.

### 4.4 Equilibrio obligatorio

La influencia de ambos referentes debe ser sutil. No mezclar elementos
visuales de forma arbitraria. La prioridad es:

1.  Comprensión de la información agrícola.
2.  Usabilidad y accesibilidad.
3.  Coherencia de la identidad visual.
4.  Ambientación y detalles decorativos.

------------------------------------------------------------------------

## 5. Componentes y patrones de interfaz

### 5.1 Paneles y superficies

-   Usar `--color-panel` para superficies que necesiten distinguirse del
    fondo.
-   Usar `--color-border` para contornos y separadores.
-   Evitar tarjetas anidadas sin necesidad.
-   No aplicar una tarjeta independiente a cada dato si puede formar
    parte de una sección, tabla, lista o panel.
-   No utilizar sombras grandes ni efectos de elevación como recurso de
    jerarquía.
-   No usar transparencias borrosas para simular vidrio.

### 5.2 Botones

-   Deben tener una acción y un propósito claros.
-   Mantener una jerarquía consistente entre acción principal,
    secundaria y destructiva.
-   Usar turquesa o naranja solo cuando el significado de la acción lo
    justifique.
-   No convertir todos los botones en botones de acento.
-   Estados `hover`, `focus`, `active` y `disabled` deben ser visibles,
    discretos y coherentes con la paleta.
-   No usar brillos, gradientes decorativos, bordes luminosos ni
    animaciones de rebote.

### 5.3 Formularios y filtros

-   Etiquetas visibles y comprensibles.
-   Controles con dimensiones cómodas y estados claramente
    diferenciados.
-   Mantener la misma apariencia en filtros equivalentes.
-   No reemplazar etiquetas por iconos ambiguos.
-   No ocultar información esencial dentro de tooltips.
-   Los filtros geográficos y temporales deben conservar su contexto al
    actualizar resultados, siempre que el comportamiento funcional
    existente lo permita.

### 5.4 Mapas y visualizaciones geográficas

-   El mapa es un área de trabajo principal, no una imagen decorativa.
-   Los controles deben permanecer agrupados y no tapar información
    geográfica importante.
-   La leyenda debe explicar las capas, unidades, rangos y significado
    de los colores.
-   Los marcadores deben tener una semántica consistente.
-   No agregar marcadores, capas, cuadrículas, datos ficticios ni
    controles que no hayan sido solicitados.
-   No usar un gradiente sin una escala y una leyenda.
-   Evitar animar continuamente el mapa o sus marcadores.
-   Las transiciones de capas deben ser breves y no bloquear la
    interacción.
-   No sacrificar rendimiento del mapa por efectos visuales.

### 5.5 Gráficos y datos

-   Cada gráfico debe comunicar una idea principal.
-   Evitar múltiples series destacadas simultáneamente si una sola
    historia es suficiente.
-   Usar el turquesa para series ambientales o valores de referencia
    cuando corresponda.
-   Reservar el naranja para el dato, periodo o anomalía que se quiera
    destacar.
-   Los ejes, unidades, fechas y leyendas deben ser legibles.
-   No ocultar valores importantes para conseguir una composición
    minimalista.
-   No añadir efectos 3D, brillos, degradados decorativos ni animaciones
    continuas.
-   Las animaciones de entrada de gráficos deben ser breves y no
    retrasar la lectura.

------------------------------------------------------------------------

## 6. Animaciones y microinteracciones

Las animaciones deben reforzar la sensación de exploración y de mundo
natural. No deben parecer efectos de una plantilla de landing page
generada por IA.

### 6.1 Animaciones permitidas

-   Aparición breve de paneles cuando se abre una sección.
-   Transiciones suaves al cambiar de pestaña o filtro.
-   Resaltado discreto de un punto o dato seleccionado.
-   Progresión controlada al cargar una visualización.
-   Movimiento sutil de elementos ambientales decorativos, solo si ya
    forman parte del diseño aprobado.
-   Transiciones de mapa o capas cuando ayuden a comprender el cambio.
-   Microinteracciones en botones y controles que confirmen la
    interacción.

### 6.2 Reglas de movimiento

-   Priorizar transiciones cortas, generalmente entre 120 y 250 ms para
    controles.
-   Usar duraciones mayores solo para transiciones de contexto que lo
    justifiquen.
-   Preferir curvas de aceleración y desaceleración naturales
    (`ease-out`, `ease-in-out`).
-   Evitar rebotes, elasticidad excesiva y movimientos bruscos.
-   No animar todos los elementos al cargar la página.
-   No hacer que los elementos floten continuamente.
-   No usar parallax intenso ni movimiento que distraiga de mapas o
    gráficos.
-   No introducir animaciones que retrasen el acceso a una acción.
-   Respetar `prefers-reduced-motion`; ofrecer una experiencia
    equivalente sin movimiento no esencial.

### 6.3 Prohibiciones de animación

No implementar por iniciativa propia:

-   Partículas flotantes por toda la pantalla.
-   Estrellas animadas como fondo permanente.
-   Nebulosas, ondas o manchas luminosas decorativas.
-   Cursores personalizados con efectos.
-   Texto que se escribe solo (typewriter) en títulos o contenido.
-   Efectos de aparición escalonada en cada elemento de una lista.
-   Botones que pulsan, respiran o brillan continuamente.
-   Tarjetas que giran, saltan o se elevan exageradamente.
-   Fondos con movimiento constante.
-   Animaciones que simulen carga cuando no existe una operación real.

------------------------------------------------------------------------

## 7. Efectos visuales expresamente prohibidos

No utilizar los siguientes recursos salvo autorización explícita del
equipo:

-   Glassmorphism o paneles de vidrio esmerilado.
-   Neumorphism.
-   Gradientes decorativos en fondos o botones.
-   Glow, neón, resplandores y bordes luminosos.
-   Sombras grandes, difusas o múltiples.
-   Esferas, blobs o manchas abstractas de colores.
-   Fondos con mallas, ruido o patrones generados solo para rellenar
    espacio.
-   Degradados morado-azul típicos de interfaces genéricas de IA.
-   Exceso de transparencias y desenfoque.
-   Tarjetas redondeadas repetidas para absolutamente todo.
-   Iconos emoji como sustitutos de iconografía de interfaz.
-   Ilustraciones de stock que no aporten información.
-   Secciones hero gigantes con frases de marketing genéricas.
-   Contadores, métricas o gráficos inventados para decorar.
-   Efectos de scroll que secuestren o dificulten la navegación.

------------------------------------------------------------------------

## 8. Tipografía e iconografía

-   Priorizar legibilidad en pantallas de escritorio y móviles.
-   Usar una familia tipográfica consistente para la interfaz.
-   Reservar fuentes de apariencia pixel art para detalles muy
    puntuales, nunca para contenido extenso o datos.
-   Mantener jerarquía clara entre títulos, subtítulos, etiquetas,
    valores y texto auxiliar.
-   Evitar tamaños diminutos en leyendas, escalas y controles de mapas.
-   Usar iconografía consistente y de un mismo estilo.
-   No combinar arbitrariamente iconos outline, sólidos, emojis y
    símbolos decorativos.
-   Los iconos deben comunicar una acción o categoría reconocible.
-   No sustituir texto importante por un icono sin etiqueta o
    alternativa accesible.

No introducir una tipografía nueva ni una librería de iconos sin revisar
primero las dependencias y convenciones ya existentes en el proyecto.

------------------------------------------------------------------------

## 9. Diseño adaptable

La interfaz debe funcionar en escritorio, tablet y móvil.

-   No asumir que el usuario dispone de una pantalla grande.
-   En móvil, reorganizar paneles y controles sin eliminar funciones
    esenciales.
-   Evitar que las leyendas, filtros o controles cubran el área útil del
    mapa.
-   Las tablas extensas deben tener una estrategia de adaptación
    definida; no comprimirlas hasta volverlas ilegibles.
-   Mantener áreas táctiles cómodas.
-   Evitar scroll horizontal de toda la página.
-   No cambiar la identidad visual entre tamaños de pantalla.
-   No crear una versión móvil visualmente distinta sin una necesidad
    funcional.

------------------------------------------------------------------------

## 10. Accesibilidad y lectura de datos

-   Mantener contraste suficiente entre texto y superficie.
-   No depender exclusivamente del color para comunicar riesgo, anomalía
    o estado.
-   Acompañar estados importantes con texto, icono o patrón.
-   Mantener foco de teclado visible.
-   Los controles deben tener etiquetas accesibles.
-   Las animaciones no esenciales deben poder reducirse.
-   Las leyendas deben explicar unidades y rangos.
-   Los gráficos deben ofrecer información equivalente en texto, tabla o
    descripción cuando sea necesario.
-   No utilizar `--color-text-muted` para información crítica si el
    contraste resulta insuficiente.
-   No reducir el contraste para conseguir una apariencia más
    atmosférica.

------------------------------------------------------------------------

## 11. Reglas de implementación para agentes de IA

Estas reglas tienen prioridad sobre preferencias estéticas inferidas por
el agente.

### 11.1 Antes de modificar

1.  Inspeccionar la estructura actual del proyecto.
2.  Identificar framework, librerías, sistema de estilos, componentes
    reutilizables y convenciones existentes.
3.  Revisar los componentes relacionados con la tarea antes de crear
    otros.
4.  Identificar qué partes son funcionales y no deben alterarse.
5.  Mantener la arquitectura y los patrones existentes, salvo que el
    usuario solicite expresamente cambiarlos.

### 11.2 Al implementar

-   Resolver únicamente el alcance solicitado.
-   Reutilizar componentes y tokens existentes.
-   Mantener separados estructura, estilos y lógica según la
    organización actual del proyecto.
-   No duplicar componentes que ya cumplen la misma función.
-   No añadir dependencias para resolver algo que puede hacerse con las
    herramientas existentes.
-   No cambiar el framework, la arquitectura, las rutas ni la gestión de
    estado sin autorización.
-   No reemplazar datos reales por datos ficticios.
-   No inventar endpoints, funcionalidades, campos, estados o reglas de
    negocio.
-   No modificar contratos de API ni modelos de datos por razones
    visuales.
-   No alterar el comportamiento funcional mientras se realiza un cambio
    de diseño.
-   No añadir comentarios innecesarios ni documentación dentro del
    código si no se solicita.
-   No cambiar nombres, rutas o estructura de archivos fuera del alcance
    solicitado.
-   No implementar funcionalidades "adicionales" porque parezcan
    convenientes.

### 11.3 Si falta información

-   No asumir que una idea visual equivale a un requisito funcional.
-   No inventar estados o categorías para completar una pantalla.
-   No inventar colores.
-   No inventar contenido, métricas, datos de ejemplo ni resultados.
-   Si falta una decisión imprescindible, preguntar antes de
    implementarla.
-   Si el detalle faltante no impide avanzar, conservar el patrón
    existente y señalar la decisión tomada.

### 11.4 Al finalizar

Comprobar:

-   Que se utilizaron exclusivamente los colores autorizados y sus
    derivados permitidos.
-   Que los componentes mantienen coherencia visual.
-   Que no se añadieron efectos prohibidos.
-   Que las animaciones son funcionales, breves y reducibles.
-   Que la interfaz es adaptable y legible.
-   Que no se alteró la lógica existente.
-   Que no se agregaron funcionalidades no solicitadas.
-   Que no se dejaron estilos temporales, valores aleatorios o datos
    ficticios.
-   Que el resultado coincide con la referencia y con el alcance
    solicitado.

------------------------------------------------------------------------

## 12. Criterios de aceptación visual

Una implementación se considera alineada con esta guía solo si cumple
todos estos puntos:

-   [ ] Utiliza los siete colores base establecidos.
-   [ ] Los colores de riesgo se usan únicamente para sus categorías
    semánticas.
-   [ ] Los gradientes solo representan escalas de datos y derivan de la
    paleta aprobada.
-   [ ] La interfaz mantiene el fondo oscuro y los paneles definidos.
-   [ ] La jerarquía de texto es clara y legible.
-   [ ] La composición transmite exploración, naturaleza y análisis
    agrícola sin imitar literalmente los juegos de referencia.
-   [ ] No presenta glassmorphism, neón, glow ni gradientes decorativos.
-   [ ] No utiliza tarjetas, sombras o bordes redondeados en exceso.
-   [ ] Las animaciones no distraen ni bloquean el uso.
-   [ ] La información geográfica y científica conserva prioridad sobre
    la decoración.
-   [ ] La interfaz se adapta a diferentes tamaños de pantalla.
-   [ ] No se añadieron funciones, datos, colores ni dependencias que no
    hayan sido solicitados.

------------------------------------------------------------------------

## 13. Instrucción final para el agente

**No rediseñes libremente el producto. No completes los requisitos con
tendencias visuales propias. No agregues elementos porque "se verían
bien".**

Usa esta guía como contrato visual. Respeta la paleta, la jerarquía, los
patrones y las restricciones. La creatividad debe expresarse en la
composición, los detalles y las microinteracciones dentro de estos
límites, nunca mediante la creación de una nueva identidad visual.

Cuando una solicitud contradiga esta guía, sigue la instrucción
explícita más reciente del usuario para esa tarea concreta. No extiendas
esa excepción a otras pantallas o componentes.
