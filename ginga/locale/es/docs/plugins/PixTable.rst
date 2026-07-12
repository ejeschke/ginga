
``PixTable`` proporciona una forma de comprobar o monitorizar los valores de los
píxeles en una región.

**Tipo de complemento: Local**

``PixTable`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso básico**

En el uso más básico, simplemente mueva el cursor por el visor de canal;
aparecerá un array de valores de píxel en la visualización «Pixel Values» de la
interfaz del complemento.  El valor central está resaltado, y corresponde al
valor bajo el cursor.

Puede elegir una cuadrícula de 3x3, 5x5, 7x7 o 9x9 en el control de cuadro
combinado más a la izquierda.  Puede ayudar ajustar el control «Tamaño de
fuente» para evitar que los valores del array se corten en los lados.  También
puede ampliar el espacio de trabajo del complemento para ver más de la tabla.

.. note:: El orden de la tabla de valores mostrada no coincidirá necesariamente
          con el visor de canal si la imagen está volteada, transpuesta o
          rotada.

**Usar marcas**

Cuando establece y selecciona una marca, los valores de píxel se mostrarán
alrededor de la marca en lugar del cursor.  Puede haber cualquier número de
marcas, y cada una se indica con una «X» numerada.  Simplemente cambie el
control desplegable de marcas para seleccionar una marca diferente y ver los
valores a su alrededor.  La marca seleccionada actualmente se muestra con un
color diferente al de las demás.

Las marcas permanecerán en su posición incluso si se carga una nueva imagen y
mostrarán los valores de la nueva imagen.  De esta forma puede monitorizar el
área alrededor de un punto si la imagen se actualiza con frecuencia.

Si la casilla «Desplazar a marca» está seleccionada, entonces cuando seleccione
una marca diferente en el control de marcas, el visor de canal se desplazará a
esa marca.  Esto puede ser útil para inspeccionar los mismos puntos en varias
imágenes diferentes, especialmente cuando se hace mucho zoom en la imagen.

.. note:: Si vuelve a cambiar el control de marcas a «None», la tabla de píxeles
          volverá a actualizarse a medida que mueva el cursor por el visor.

El cuadro «Caption» se puede usar para establecer una anotación de texto que se
añadirá a la etiqueta de la marca cuando se cree la siguiente marca.  Esto puede
usarse para etiquetar una característica en la imagen, por ejemplo.

**Eliminar marcas**

Para eliminar una marca, selecciónela en el control de marcas y luego pulse el
botón etiquetado «Eliminar».  Para eliminar todas las marcas, pulse el botón
etiquetado «Eliminar todo».

**Mover marcas**

Cuando el botón de radio «Mover» está marcado y hay una marca seleccionada,
entonces hacer clic o arrastrar en cualquier lugar de la imagen moverá la marca
a esa ubicación y actualizará la tabla de píxeles.  Si no hay ninguna marca
seleccionada actualmente, se creará una nueva y se moverá.

**Dibujar marcas**

Cuando el botón de radio «Dibujar» está marcado, hacer clic y arrastrar crea una
nueva marca.  Cuanto más largo sea el trazo, mayor será el radio de la «X».

**Editar marcas**

Cuando el botón de radio «Editar» está marcado después de haber seleccionado una
marca, puede arrastrar los puntos de control de la marca para aumentar el radio
de los brazos de la X, o puede arrastrar el cuadro delimitador para mover la
marca.  Si los puntos de control de edición no se muestran, simplemente haga
clic en el centro de una marca para habilitarlos.

**Teclas especiales**

En modo «Mover» las siguientes teclas están activas:
- «n» colocará una nueva marca en el lugar del cursor
- «m» moverá la marca actual (si la hay) al lugar del cursor
- «d» eliminará la marca actual (si la hay)
- «j» seleccionará la marca anterior (si la hay)
- «k» seleccionará la marca siguiente (si la hay)

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_PixTable.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # PixTable plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_PixTable.cfg"

  # Default font
  font = 'fixed'

  # Default font size
  fontsize = 12

  # default size for mark point radius
  mark_radius = 10

  # style of point to draw
  mark_style = 'cross'

  # color of non-selected marks
  mark_color = 'purple'

  # color of selected mark
  select_color = 'cyan'

  # whether to update the pixel table when moving a mark around
  drag_update = True
