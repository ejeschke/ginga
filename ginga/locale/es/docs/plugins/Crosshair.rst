
``Crosshair`` es un complemento sencillo para dibujar cruces filares etiquetadas
con la posición de la cruz en coordenadas de píxel, coordenadas WCS o el valor
de dato en la posición de la cruz.

**Tipo de complemento: Local**

``Crosshair`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Seleccione el tipo de salida apropiado en el cuadro desplegable «Format» de la
interfaz: «xy» para coordenadas de píxel, «coords» para las coordenadas WCS y
«value» para el valor en la posición de la cruz filar.

Si «Solo arrastrar» está marcado, la cruz filar solo se actualiza cuando se hace
clic o se arrastra el cursor en la ventana.  Si está desmarcado, la cruz filar
se posiciona simplemente moviendo el cursor por la ventana del visor de canal.

La pestaña «Cuts» contiene un gráfico de perfil de los cortes vertical y
horizontal representados por el límite visible de la caja presente cuando «Quick
Cuts» está marcado.  Este gráfico se actualiza en tiempo real a medida que se
mueve la cruz filar.  Cuando «Quick Cuts» está desmarcado, el gráfico no se
actualiza.

El tamaño de la caja se determina por el parámetro «radius».

El control «Nivel de aviso» se puede usar para establecer un nivel de flujo por
encima del cual se indica un aviso en el gráfico de cortes mediante una línea
amarilla y el fondo volviéndose amarillo.  El aviso se activa si algún valor a
lo largo del corte X o Y supera el umbral del nivel de aviso.

El control «Nivel de alerta» es similar, pero se representa mediante una línea
roja y el fondo volviéndose rosa.  El aviso se activa si algún valor a lo largo
del corte X o Y supera el umbral del nivel de alerta.  Las alertas tienen
prioridad sobre los avisos.

Tanto la función «Aviso» como «Alerta» se pueden desactivar simplemente
estableciendo un valor en blanco.  Están desactivadas de forma predeterminada.

El gráfico de cortes es interactivo, pero solo tiene sentido usarlo si «Solo
arrastrar» está marcado.  Puede pulsar «x» o «y» en la ventana del gráfico para
activar y desactivar la función de escalado automático de ejes para cualquiera
de los ejes, y desplazarse en el gráfico para hacer zoom en el eje X (mantenga
pulsada Ctrl mientras se desplaza para hacer zoom en el eje Y).

Crosshair proporciona una función de interacción con el complemento Pick: cuando
la cruz filar está sobre un objeto, puede pulsar «r» en la ventana del visor de
canal para que el complemento Pick se invoque en esa ubicación concreta.  Si aún
no hay un Pick abierto en ese canal, se abrirá primero.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_Crosshair.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # Crosshair plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Crosshair.cfg"

  # color of the crosshair
  color = 'green'

  # text color of crosshair
  text_color = 'skyblue'

  # box color indicating cut radius
  box_color = 'aquamarine'

  # cut plot line colors for X and Y
  quick_h_cross_color = '#7570b3'
  quick_v_cross_color = '#1b9e77'

  # enable quick cuts plots by default
  quick_cuts = False

  # force drag only by default
  drag_only = False

  # set a warning level for the warning feature of the cuts plot
  warn_level = None

  # set an alery level for the alert feature of the cuts plot
  alert_level = None

  # set initial radius of the cuts box
  cuts_radius = 15
