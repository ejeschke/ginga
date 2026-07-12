
Un complemento para generar un gráfico de los valores a lo largo de una línea o
un camino.

**Tipo de complemento: Local**

``Cuts`` es un complemento local, lo que significa que está asociado a un canal.
No es un singleton, lo que significa que se pueden abrir varias instancias para
cada canal.

**Uso**

``Cuts`` representa un gráfico sencillo de valores de píxel frente al índice para
una línea dibujada a través de la imagen.  Se pueden representar varios cortes.

Hay cuatro tipos de cortes disponibles: line, path, freepath y beziercurve:

* El corte «line» es una línea recta entre dos puntos.
* El corte «path» se dibuja como un polígono abierto, con segmentos rectos
  entre medias.
* El corte «freepath» es como un corte path, pero se dibuja con un trazo libre
  que sigue el movimiento del cursor.
* El camino «beziercurve» es una curva de Bézier cúbica.

Si se añade una nueva imagen al canal mientras el complemento está activo, este
se actualizará con los nuevos cortes calculados en la nueva imagen.

Si el ajuste «enable slit» está habilitado, este complemento también permitirá
la funcionalidad de imagen de rendija (para imágenes multidimensionales)
mediante una pestaña «Slit».  En la interfaz de la pestaña, seleccione un eje de
la lista «Axes» y dibuje una línea.  Esto creará una imagen 2D que asume que los
dos primeros ejes son espaciales e indexa los datos a lo largo del eje
seleccionado.  Al igual que con ``Cuts``, puede ver las otras imágenes de
rendija usando el cuadro desplegable de selección de corte.

**Dibujar cortes**

El menú «New Cut Type» le permite elegir qué tipo de corte va a dibujar.

Elija «New Cut» en el menú desplegable «Cut» si desea dibujar un corte nuevo.  De
lo contrario, si hay un corte con nombre concreto seleccionado, este será
reemplazado por cualquier corte recién dibujado.

Mientras dibuja un corte path o beziercurve, pulse «v» para añadir un vértice, o
«z» para eliminar el último vértice añadido.

**Atajos de teclado**

Mientras pasa el cursor por encima, pulse «h» para un corte horizontal completo
y «j» para un corte vertical completo.

**Eliminar cortes**

Para eliminar un corte, seleccione su nombre en el desplegable «Cut» y haga clic
en el botón «Eliminar».  Para eliminar todos los cortes, pulse «Eliminar todo».

**Editar cortes**

Usando la función de edición del lienzo, es posible añadir nuevos vértices a un
camino existente y mover vértices.  Haga clic en el botón de radio «Editar» para
poner el lienzo en modo edición.  Si un corte no se selecciona automáticamente,
ahora puede seleccionar la línea, el camino o la curva haciendo clic en ella, lo
que debería habilitar los puntos de control en los extremos o vértices -- puede
arrastrarlos.  Para añadir un nuevo vértice a un camino, pase el cursor con
cuidado sobre la línea donde desea el nuevo vértice y pulse «v».  Para eliminar
un vértice, pase el cursor sobre él y pulse «z».

Notará un punto de control adicional en la mayoría de los objetos, que tiene un
centro de un color diferente -- este es un punto de control de movimiento para
mover todo el objeto por la imagen cuando está en modo edición.

También puede seleccionar «Mover» para simplemente mover un corte sin cambios.

**Cambiar la anchura de los cortes**

La anchura de los cortes «line» se puede cambiar usando el menú «Width Type»:

* «none» indica un corte de radio cero; es decir, mostrando solo los valores de
  píxel a lo largo de la línea
* «x» representará la suma de valores a lo largo del eje X ortogonal al corte.
* «y» representará la suma de valores a lo largo del eje Y ortogonal al corte.
* «perpendicular» representará la suma de valores a lo largo de un eje
  perpendicular al corte.

El «Width radius» controla la anchura de la sumación ortogonal en una cantidad a
cada lado del corte -- 1 serían 3 píxeles, 2 serían 5 píxeles, etc.

**Guardar cortes**

Use el botón «Guardar» para guardar el gráfico de ``Cuts`` como imagen y los
datos como un archivo comprimido de Numpy.

**Copiar cortes**

Para copiar un corte, seleccione su nombre en el desplegable «Cut» y haga clic en
el botón «Copiar corte».  Se creará un nuevo corte a partir de él.  Luego puede
manipular el nuevo corte de forma independiente.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_Cuts.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Cuts plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Cuts.cfg"

  # If set to True will always select a cut after drawing it
  select_new_cut = True

  # If set to True will automatically change to "move" mode after draw
  draw_then_move = True

  # If set to True will label cuts with a text annotation
  label_cuts = True

  # If set to True will add a legend to the cuts plot
  show_cuts_legend = False

  # If set to True will add Slit tab
  enable_slit = False

  # Default cut colors
  colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink', 'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']

  # If set to True, will update graph continuously as cursor is dragged
  # around image
  drag_update = False
