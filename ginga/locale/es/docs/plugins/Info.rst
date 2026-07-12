
El complemento ``Info`` proporciona un panel de metadatos comúnmente útiles sobre
la imagen del canal enfocado.  La información común incluye algunos valores de
cabecera de metadatos, coordenadas, dimensiones de la imagen, valores mínimo y
máximo, etc.  A medida que se mueve el cursor por la imagen, los valores X, Y,
Value, RA y DEC se actualizan para reflejar el valor bajo el cursor.

**Tipo de complemento: Global**

``Info`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

En la parte inferior de la interfaz de ``Info`` están los controles de
distribución de color y de niveles de corte.  El selector encima de los cuadros
de niveles de corte le permite elegir entre varios algoritmos de distribución
que mapean los valores de la imagen al mapa de color.  Las opciones son
«linear», «log», «power», «sqrt», «squared», «asinh», «sinh» y «histeq»
(ecualización de histograma).

Debajo de esto, se muestran los niveles de corte bajo y alto y se pueden
ajustar.  Al pulsar el botón «Auto Levels» se recalcularán los niveles de corte
basándose en el algoritmo actual de niveles de corte automáticos y los
parámetros definidos en las preferencias del canal.

Debajo del botón «Auto Levels», se muestra el estado de los ajustes de «Cut New»,
«Zoom New» y «Center New» para el canal actualmente activo.  Estos indican cómo
las nuevas imágenes que se añaden al canal se verán afectadas por los niveles de
corte automáticos, el ajuste a la ventana y el desplazamiento al centro de la
imagen.

La casilla «Follow New» controla si el visor mostrará automáticamente las nuevas
imágenes añadidas al canal.  La casilla «Raise New» controla si una ventana del
visor de imágenes se eleva cuando se añade una nueva imagen.  Estos dos controles
pueden ser útiles, por ejemplo, si un programa externo está añadiendo imágenes al
visor, y desea evitar la interrupción de su trabajo al examinar una imagen en
particular.

Como complemento global, ``Info`` responde a un cambio de enfoque a un nuevo
canal mostrando los metadatos del nuevo canal.  Normalmente aparece bajo la
pestaña «Synopsis» en la interfaz de usuario.

Este complemento no suele configurarse para poder cerrarse, pero el usuario puede
hacer que lo sea estableciendo el ajuste «closeable» en True en el archivo de
configuración; entonces se añadirán los botones Cerrar y Ayuda en la parte
inferior de la interfaz.
