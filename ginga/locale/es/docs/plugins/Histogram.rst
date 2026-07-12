
``Histogram`` representa un histograma de una región dibujada en la imagen, o de
la imagen entera.

**Tipo de complemento: Local**

``Histogram`` es un complemento local, lo que significa que está asociado a un
canal.  No es un singleton, lo que significa que se pueden abrir varias
instancias para cada canal.

**Uso**

Haga clic y arrastre para definir una región dentro de la imagen que se usará
para calcular el histograma.  Para tomar el histograma de la imagen completa,
haga clic en el botón de la interfaz etiquetado «Imagen completa».

.. note:: Según el tamaño de la imagen, calcular el histograma completo puede
          llevar tiempo.

Si se selecciona una nueva imagen para el canal, el gráfico del histograma se
recalculará según los parámetros actuales con los nuevos datos.

A menos que se deshabilite en el archivo de ajustes del complemento de
histograma, se calcula una línea de estadísticas sencillas para la caja y se
muestra en una línea debajo del gráfico.

**Controles de la interfaz**

Tres botones de radio en la parte inferior de la interfaz se usan para controlar
los efectos de la acción de clic/arrastre:

* seleccione «Mover» para arrastrar la región a una ubicación diferente
* seleccione «Dibujar» para dibujar una nueva región
* seleccione «Editar» para editar la región

Para hacer un gráfico logarítmico del histograma, marque la casilla «Histograma
logarítmico».  Para representar por el rango completo de valores de la imagen en
lugar de por el rango dentro de los valores de corte, desmarque la casilla
«Representar por cortes».

El parámetro «NumBins» determina cuántos contenedores se usan al calcular el
histograma.  Escriba un número en el cuadro y pulse «Enter» para cambiar el
valor predeterminado.

**Controles prácticos de niveles de corte**

Como un histograma es una retroalimentación útil para establecer los niveles de
corte, se proporcionan controles en la interfaz para establecer los niveles de
corte bajo y alto en la imagen, así como para realizar unos niveles de corte
automáticos, según los ajustes de niveles de corte automáticos de las
preferencias del canal.

Puede establecer niveles de corte haciendo clic en el gráfico del histograma:

* clic izquierdo: establecer corte bajo
* clic central: restablecer (niveles de corte automáticos)
* clic derecho: establecer corte alto

Además, puede ajustar dinámicamente el hueco entre los cortes bajo y alto
desplazando la rueda en el gráfico (es decir, la «anchura» de la curva del
gráfico del histograma).  Esto tiene el efecto de aumentar o disminuir el
contraste dentro de la imagen.  La cantidad que se cambia por cada clic de rueda
se establece mediante el ajuste ``scroll_pct`` del archivo de configuración del
complemento.  El valor predeterminado es 10 %.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_Histogram.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
